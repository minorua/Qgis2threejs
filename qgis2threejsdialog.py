# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejsDialog
                                 A QGIS plugin
 export terrain and map image into web browser
                             -------------------
        begin                : 2013-12-21
        copyright            : (C) 2013 Minoru Akagi
        email                : akaginch@gmail.com

 RectangleMapTool class is from extentSelector.py of GdalTools plugin
        copyright            : (C) 2010 by Giuseppe Sucameli
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import QgsMessageBar, QgsMapToolEmitPoint, QgsRubberBand
from ui_qgis2threejsdialog import Ui_Qgis2threejsDialog

from qgis2threejsmain import *
import qgis2threejstools as tools
from quadtree import *
from vectorobject import *
from vectorstylewidgets import *

debug_mode = 1

class Qgis2threejsDialog(QDialog):
  STYLE_MAX_COUNT = 3

  def __init__(self, iface):
    QDialog.__init__(self, iface.mainWindow())
    self.iface = iface
    self.apiChanged22 = False   # not QgsApplication.prefixPath().startswith("C:/OSGeo4W")  # QGis.QGIS_VERSION_INT >= 20200

    # Set up the user interface from Designer.
    self.ui = ui = Ui_Qgis2threejsDialog()
    ui.setupUi(self)

    self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)
    ui.lineEdit_OutputFilename.setPlaceholderText("[Temporary file]")

    ui.pushButton_Run.clicked.connect(self.run)
    ui.pushButton_Close.clicked.connect(self.reject)

    # DEM tab
    ui.toolButton_switchFocusMode.setVisible(False)
    ui.toolButton_PointTool.setVisible(False)
    ui.progressBar.setVisible(False)
    self.switchFocusMode(True)

    ui.checkBox_useDEM.toggled.connect(self.useDemToggled)
    ui.toolButton_Browse.clicked.connect(self.browseClicked)
    ui.radioButton_Simple.toggled.connect(self.samplingModeChanged)
    ui.horizontalSlider_Resolution.valueChanged.connect(self.calculateResolution)
    ui.spinBox_Height.valueChanged.connect(self.updateQuads)
    ui.toolButton_switchFocusMode.clicked.connect(self.switchFocusModeClicked)
    ui.toolButton_PointTool.clicked.connect(self.startPointSelection)

    # Vector tab
    ui.treeWidget_VectorLayers.setHeaderLabel("Vector layers")
    self.initVectorStyleWidgets()

    ui.treeWidget_VectorLayers.currentItemChanged.connect(self.currentVectorLayerChanged)
    ui.treeWidget_VectorLayers.itemChanged.connect(self.vectorLayerItemChanged)
    ui.comboBox_ObjectType.currentIndexChanged.connect(self.objectTypeSelectionChanged)

    self.bar = None
    self.localBrowsingMode = True
    self.rb_quads = self.rb_point = None
    self.currentVectorLayer = None
    self.vectorPropertiesDict = {}
    self.objectTypeManager = ObjectTypeManager()

    # set map tool
    self.previousMapTool = None
    self.mapTool = RectangleMapTool(iface.mapCanvas())
    self.connect(self.mapTool, SIGNAL("rectangleCreated()"), self.rectangleSelected)
#    self.mapTool = PointMapTool(iface.mapCanvas())
#    QObject.connect(self.mapTool, SIGNAL("pointSelected()"), self.pointSelected)
    iface.mapCanvas().mapToolSet.connect(self.mapToolSet)
    self.startPointSelection()

  def exec_(self):
    ui = self.ui
    messages = []
    # show message if crs unit is degrees
    mapSettings = self.iface.mapCanvas().mapSettings() if self.apiChanged22 else self.iface.mapCanvas().mapRenderer()
    if mapSettings.destinationCrs().mapUnits() in [QGis.Degrees]:
      self.showMessageBar("The unit of current CRS is degrees", "Terrain may not appear well.")

    # show message if there are no dem layer
    no_demlayer = ui.comboBox_DEMLayer.count() == 0
    if no_demlayer:
      ui.checkBox_useDEM.setEnabled(False)
      ui.checkBox_useDEM.setChecked(False)

    return QDialog.exec_(self)

  def showMessageBar(self, title, text, level=QgsMessageBar.INFO):
    if self.bar is None:
      self.bar = QgsMessageBar()
      self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)

      ui = self.ui
      margins = ui.gridLayout.getContentsMargins()
      vl = ui.gridLayout.takeAt(0)
      ui.gridLayout.setContentsMargins(0,0,0,0)
      ui.gridLayout.addWidget(self.bar, 0, 0)
      ui.gridLayout.addItem(vl, 1, 0)
      ui.verticalLayout.setContentsMargins(margins[0], margins[1] / 2, margins[2], margins[3])
    self.bar.pushMessage(title, text, level=level)

  def initTemplateList(self, templateName=""):
    self.ui.comboBox_Template.clear()
    templateDir = QDir(tools.templateDir())
    for entry in templateDir.entryList(["*.html", "*.htm"]):
      self.ui.comboBox_Template.addItem(entry)

    if templateName:
      index = self.ui.comboBox_Template.findText(templateName)
      if index != -1:
        self.ui.comboBox_Template.setCurrentIndex(index)
      return index
    return -1

  def initDEMLayerList(self, layerId=None):
    # list 1 band raster layers
    self.ui.comboBox_DEMLayer.clear()
    for id, layer in QgsMapLayerRegistry().instance().mapLayers().items():
      if layer.type() == QgsMapLayer.RasterLayer and layer.providerType() == "gdal" and layer.bandCount() == 1:
        self.ui.comboBox_DEMLayer.addItem(layer.name(), id)

    # select the last selected layer
    if layerId is not None:
      index = self.ui.comboBox_DEMLayer.findData(layerId)
      if index != -1:
        self.ui.comboBox_DEMLayer.setCurrentIndex(index)
      return index
    return -1

  def initVectorLayerTree(self, vectorPropertiesDict):
    self.vectorPropertiesDict = vectorPropertiesDict
    tree = self.ui.treeWidget_VectorLayers
    tree.clear()
    # add vector layers into tree widget
    self.treeTopItems = topItems = {QGis.Point:QTreeWidgetItem(tree, ["Point"]), QGis.Line:QTreeWidgetItem(tree, ["Line"]), QGis.Polygon:QTreeWidgetItem(tree, ["Polygon"])}
    self.vlItems = {}
    for layer in self.iface.legendInterface().layers():
      if layer.type() != QgsMapLayer.VectorLayer:
        continue
      geometry_type = layer.geometryType()
      if geometry_type in [QGis.Point, QGis.Line, QGis.Polygon]:
        self.vlItems[layer.id()] = item = QTreeWidgetItem(topItems[geometry_type], [layer.name()])
        if layer.id() in self.vectorPropertiesDict:
          isVisible = self.vectorPropertiesDict[layer.id()]["visible"]
        else:
          isVisible = False   #self.iface.legendInterface().isLayerVisible(layer)
        check_state = Qt.Checked if isVisible else Qt.Unchecked
        item.setData(0, Qt.CheckStateRole, check_state)
        item.setData(0, Qt.UserRole, layer.id())
        #item.setDisabled(True)
        #item.setData(0, Qt.CheckStateRole, Qt.Unchecked)

    for item in topItems.values():
      tree.expandItem(item)

    self.setVectorStylesEnabled(False)

  def initVectorStyleWidgets(self):
    self.colorWidget = StyleWidget(StyleWidget.COLOR)
    self.ui.verticalLayout_Styles.addWidget(self.colorWidget)
    self.heightWidget = StyleWidget(StyleWidget.HEIGHT)
    self.ui.verticalLayout_zCoordinate.addWidget(self.heightWidget)

    self.styleWidgets = []
    for i in range(self.STYLE_MAX_COUNT):
      widget = StyleWidget()
      widget.setVisible(False)
      self.ui.verticalLayout_Styles.addWidget(widget)
      self.styleWidgets.append(widget)

  def currentVectorLayerChanged(self, currentItem, previousItem):
    # save properties of previous item
    if previousItem is not None:
      layerid = previousItem.data(0, Qt.UserRole)
      if layerid is not None:
        self.saveVectorProperties(layerid)

    layerid = currentItem.data(0, Qt.UserRole)
    if layerid is None:
      self.currentVectorLayer = None
      return
    self.currentVectorLayer = layer = QgsMapLayerRegistry().instance().mapLayer(layerid)
    if layer is None:
      return

    for i in range(self.STYLE_MAX_COUNT):
      self.styleWidgets[i].hide()

    obj_types = self.objectTypeManager.objectTypeNames(layer.geometryType())
    ui = self.ui
    ui.comboBox_ObjectType.blockSignals(True)
    ui.comboBox_ObjectType.clear()
    ui.comboBox_ObjectType.addItems(obj_types)
    ui.comboBox_ObjectType.blockSignals(False)

    # set up property widgets
    self.objectTypeSelectionChanged()

    if layerid in self.vectorPropertiesDict:
      # restore properties
      self.restoreVectorProperties(layerid)

    self.setVectorStylesEnabled(currentItem.data(0, Qt.CheckStateRole) == Qt.Checked)

  def vectorLayerItemChanged(self, item, column):
    # update style form enablement
    currentItem = self.ui.treeWidget_VectorLayers.currentItem()
    if currentItem:
      self.setVectorStylesEnabled(currentItem.data(0, Qt.CheckStateRole) == Qt.Checked)

  def objectTypeSelectionChanged(self, idx=None):
    layer = self.currentVectorLayer
    try:
      ve = float(ui.lineEdit_zFactor.text())
    except:
      ve = 1
    mapTo3d = MapTo3D(self.iface.mapCanvas(), verticalExaggeration=ve)
    self.objectTypeManager.setupForm(self, mapTo3d, layer, layer.geometryType(), self.ui.comboBox_ObjectType.currentIndex())

  def numericFields(self, layer):
    # get attributes of a sample feature and create numeric field name list
    numeric_fields = []
    f = QgsFeature()
    layer.getFeatures().nextFeature(f)
    for field in f.fields():
      isNumeric = False
      try:
        float(f.attribute(field.name()))
        isNumeric = True
      except:
        pass
      if isNumeric:
        numeric_fields.append(field.name())
    return numeric_fields

  def setVectorStylesEnabled(self, enabled):
    self.ui.comboBox_ObjectType.setEnabled(enabled)
    self.ui.label_ObjectType.setEnabled(enabled)
    self.colorWidget.setEnabled(enabled)
    self.heightWidget.setEnabled(enabled)
    for i in range(self.STYLE_MAX_COUNT):
      self.styleWidgets[i].setEnabled(enabled)

  def saveVectorProperties(self, layerid):
    properties = {}
    layer = QgsMapLayerRegistry().instance().mapLayer(layerid)
    itemIndex = self.ui.comboBox_ObjectType.currentIndex()
    properties["itemindex"] = itemIndex
    properties["typeitem"] = self.objectTypeManager.objectTypeItem(layer.geometryType(), itemIndex)
    properties["visible"] = self.vlItems[self.currentVectorLayer.id()].data(0, Qt.CheckStateRole) == Qt.Checked
    properties["color"] = self.colorWidget.values()
    properties["height"] = self.heightWidget.values()
    for i in range(self.STYLE_MAX_COUNT):
      if self.styleWidgets[i].isVisible():
        properties[i] = self.styleWidgets[i].values()
    self.vectorPropertiesDict[layerid] = properties

  def restoreVectorProperties(self, layerid):
    properties = self.vectorPropertiesDict[layerid]
    self.ui.comboBox_ObjectType.setCurrentIndex(properties["itemindex"])
    self.colorWidget.setValues(properties["color"])
    self.heightWidget.setValues(properties["height"])
    for i in range(self.STYLE_MAX_COUNT):
      if i in properties:
        self.styleWidgets[i].setValues(properties[i])

  def calculateResolution(self, v=None):
    extent = self.iface.mapCanvas().extent()
    renderer = self.iface.mapCanvas().mapRenderer()
    size = 100 * self.ui.horizontalSlider_Resolution.value()
    self.ui.label_Resolution.setText("about {0} x {0} px".format(size))

    # calculate resolution and size
    width, height = renderer.width(), renderer.height()
    s = (size * size / float(width * height)) ** 0.5
    if s < 1:
      width = int(width * s)
      height = int(height * s)

    xres = extent.width() / width
    yres = extent.height() / height
    self.ui.lineEdit_HRes.setText(str(xres))
    self.ui.lineEdit_VRes.setText(str(yres))
    self.ui.lineEdit_Width.setText(str(width + 1))
    self.ui.lineEdit_Height.setText(str(height + 1))

  def progress(self, percentage):
    self.ui.progressBar.setValue(percentage)
    self.ui.progressBar.setVisible(percentage != 100)

  def run(self):
    ui = self.ui
    filename = ui.lineEdit_OutputFilename.text()   # ""=Temporary file
    if filename != "" and QFileInfo(filename).exists() and QMessageBox.question(None, "Qgis2threejs", "Output file already exists. Overwrite it?", QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
      return
    self.endPointSelection()

    item = ui.treeWidget_VectorLayers.currentItem()
    if item:
      self.saveVectorProperties(item.data(0, Qt.UserRole))

    ui.pushButton_Run.setEnabled(False)
    self.progress(0)

    canvas = self.iface.mapCanvas()
    templateName = ui.comboBox_Template.currentText()
    htmlfilename = ui.lineEdit_OutputFilename.text()
    if ui.checkBox_useDEM.isChecked():
      demlayerid = ui.comboBox_DEMLayer.itemData(ui.comboBox_DEMLayer.currentIndex())
    else:
      demlayerid = None
    mapTo3d = MapTo3D(canvas, verticalExaggeration=float(ui.lineEdit_zFactor.text()))
    if self.ui.radioButton_Simple.isChecked() or demlayerid is None:
      if demlayerid:
        dem_width = int(ui.lineEdit_Width.text())
        dem_height = int(ui.lineEdit_Height.text())
      else:
        dem_width = dem_height = 2
      context = OutputContext(templateName, mapTo3d, canvas, demlayerid, self.vectorPropertiesDict, self.objectTypeManager, self.localBrowsingMode,
                              dem_width, dem_height, ui.spinBox_sidetransp.value(), ui.spinBox_demtransp.value())
      htmlfilename = runSimple(htmlfilename, context, self.progress)
    else:
      context = OutputContext(templateName, mapTo3d, canvas, demlayerid, self.vectorPropertiesDict, self.objectTypeManager, self.localBrowsingMode)
      htmlfilename = runAdvanced(htmlfilename, context, self, self.progress)
    self.progress(100)
    ui.pushButton_Run.setEnabled(True)
    if htmlfilename is None:
      return
    self.clearRubberBands()

    if not tools.openHTMLFile(htmlfilename):
      return
    QDialog.accept(self)

  def reject(self):
    self.endPointSelection()
    self.clearRubberBands()
    QDialog.reject(self)

  def startPointSelection(self):
    canvas = self.iface.mapCanvas()
    self.previousMapTool = canvas.mapTool()
    canvas.setMapTool(self.mapTool)
    self.ui.toolButton_PointTool.setVisible(False)

  def endPointSelection(self):
    self.mapTool.reset()
    self.iface.mapCanvas().setMapTool(self.previousMapTool)

  def rectangleSelected(self):
    ui = self.ui
    ui.radioButton_Advanced.setChecked(True)
    rect = self.mapTool.rectangle()
    toRect = rect.width() and rect.height()
    self.switchFocusMode(toRect)
    ui.lineEdit_xmin.setText(str(rect.xMinimum()))
    ui.lineEdit_ymin.setText(str(rect.yMinimum()))
    ui.lineEdit_xmax.setText(str(rect.xMaximum()))
    ui.lineEdit_ymax.setText(str(rect.yMaximum()))

    quadtree = QuadTree(self.iface.mapCanvas().extent())
    quadtree.buildTreeByRect(rect, self.ui.spinBox_Height.value())
    self.createRubberBands(quadtree.quads(), rect.center())
    self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)

  def pointSelected(self):
    # set values of controls
    self.ui.lineEdit_CenterX.setText(str(self.mapTool.point.x()))
    self.ui.lineEdit_CenterY.setText(str(self.mapTool.point.y()))
    self.ui.radioButton_Advanced.setChecked(True)

    quadtree = QuadTree(self.iface.mapCanvas().extent(), self.mapTool.point, self.ui.spinBox_Height.value())
    self.createRubberBands(quadtree.quads(), self.mapTool.point)
    self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)

  def mapToolSet(self, mapTool):
    if mapTool != self.mapTool:
      self.ui.toolButton_PointTool.setVisible(True)

  def createQuadTree(self):
    ui = self.ui
    try:
      c = map(float, [ui.lineEdit_xmin.text(), ui.lineEdit_ymin.text(), ui.lineEdit_xmax.text(), ui.lineEdit_ymax.text()])
    except:
      return None
    quadtree = QuadTree(self.iface.mapCanvas().extent())
    quadtree.buildTreeByRect(QgsRectangle(c[0], c[1], c[2], c[3]), ui.spinBox_Height.value())
    return quadtree

  def createRubberBands(self, quads, point=None):
    self.clearRubberBands()
    # create quads with rubber band
    self.rb_quads = QgsRubberBand(self.iface.mapCanvas(), QGis.Line)
    self.rb_quads.setColor(Qt.blue)
    self.rb_quads.setWidth(1)

    for quad in quads:
      points = []
      extent = quad.extent
      points.append(QgsPoint(extent.xMinimum(), extent.yMinimum()))
      points.append(QgsPoint(extent.xMinimum(), extent.yMaximum()))
      points.append(QgsPoint(extent.xMaximum(), extent.yMaximum()))
      points.append(QgsPoint(extent.xMaximum(), extent.yMinimum()))
      self.rb_quads.addGeometry(QgsGeometry.fromPolygon([points]), None)
      self.log(extent.toString())
    self.log("Quad count: %d" % len(quads))

    # create a point with rubber band
    if point:
      self.rb_point = QgsRubberBand(self.iface.mapCanvas(), QGis.Point)
      self.rb_point.setColor(Qt.red)
      self.rb_point.addPoint(point)

  def clearRubberBands(self):
    # clear quads and point
    if self.rb_quads:
      self.iface.mapCanvas().scene().removeItem(self.rb_quads)
      self.rb_quads = None
    if self.rb_point:
      self.iface.mapCanvas().scene().removeItem(self.rb_point)
      self.rb_point = None

  def useDemToggled(self, checked):
    self.ui.comboBox_DEMLayer.setEnabled(checked)
    self.ui.groupBox.setEnabled(checked)

  def browseClicked(self):
    directory = self.ui.lineEdit_OutputFilename.text()
    if directory == "":
      directory = QDir.homePath()
    filename = QFileDialog.getSaveFileName(self, self.tr("Output filename"), directory, "HTML file (*.html *.htm)", options=QFileDialog.DontConfirmOverwrite)
    if filename != "":
      self.ui.lineEdit_OutputFilename.setText(filename)

  def samplingModeChanged(self):
    ui = self.ui
    isSimpleMode = ui.radioButton_Simple.isChecked()
    simple_widgets = [ui.horizontalSlider_Resolution, ui.lineEdit_Width, ui.lineEdit_Height, ui.lineEdit_HRes, ui.lineEdit_VRes, ui.spinBox_sidetransp, ui.spinBox_demtransp]
    for w in simple_widgets:
      w.setEnabled(isSimpleMode)

    isAdvancedMode = not isSimpleMode
    advanced_widgets = [ui.spinBox_Height, ui.lineEdit_xmin, ui.lineEdit_ymin, ui.lineEdit_xmax, ui.lineEdit_ymax, ui.toolButton_switchFocusMode]
    for w in advanced_widgets:
      w.setEnabled(isAdvancedMode)

  def updateQuads(self, v=None):
    quadtree = self.createQuadTree()
    if quadtree:
      self.createRubberBands(quadtree.quads(), quadtree.focusRect.center())
    else:
      self.clearRubberBands()

  def switchFocusModeClicked(self):
    self.switchFocusMode(not self.ui.label_xmin.isVisible())

  def switchFocusMode(self, toRect):
    ui = self.ui
    toPoint = not toRect
    ui.label_xmin.setVisible(toRect)
    ui.label_ymin.setVisible(toRect)
    ui.lineEdit_xmin.setVisible(toRect)
    ui.lineEdit_ymin.setVisible(toRect)

    suffix = "max" if toRect else ""
    ui.label_xmax.setText("x" + suffix)
    ui.label_ymax.setText("y" + suffix)
    mode = "point" if toRect else "rectangle"
    ui.toolButton_switchFocusMode.setText("To " + mode + " selection")
    selection = "area" if toRect else "point"
    action = "Stroke a rectangle" if toRect else "Click"
    ui.label_Focus.setText("Focus {0} ({1} on map canvas to set values)".format(selection, action))

  def log(self, msg):
    if debug_mode:
      qDebug(msg)

class PointMapTool(QgsMapToolEmitPoint):
  def __init__(self, canvas):
    self.canvas = canvas
    QgsMapToolEmitPoint.__init__(self, self.canvas)
    self.point = None

  def canvasPressEvent(self, e):
    self.point = self.toMapCoordinates(e.pos())
    self.emit(SIGNAL("pointSelected()"))

class RectangleMapTool(QgsMapToolEmitPoint):
  def __init__(self, canvas):
    self.canvas = canvas
    QgsMapToolEmitPoint.__init__(self, self.canvas)

    self.rubberBand = QgsRubberBand(self.canvas, QGis.Polygon)
    self.rubberBand.setColor(QColor(255, 0, 0, 180))
    self.rubberBand.setWidth(1)
    self.reset()

  def reset(self):
    self.startPoint = self.endPoint = None
    self.isEmittingPoint = False
    self.rubberBand.reset(QGis.Polygon)

  def canvasPressEvent(self, e):
    self.startPoint = self.toMapCoordinates(e.pos())
    self.endPoint = self.startPoint
    self.isEmittingPoint = True
    self.showRect(self.startPoint, self.endPoint)

  def canvasReleaseEvent(self, e):
    self.isEmittingPoint = False
    self.emit(SIGNAL("rectangleCreated()"))

  def canvasMoveEvent(self, e):
    if not self.isEmittingPoint:
      return
    self.endPoint = self.toMapCoordinates(e.pos())
    self.showRect(self.startPoint, self.endPoint)

  def showRect(self, startPoint, endPoint):
    self.rubberBand.reset(QGis.Polygon)
    if startPoint.x() == endPoint.x() or startPoint.y() == endPoint.y():
      return

    point1 = QgsPoint(startPoint.x(), startPoint.y())
    point2 = QgsPoint(startPoint.x(), endPoint.y())
    point3 = QgsPoint(endPoint.x(), endPoint.y())
    point4 = QgsPoint(endPoint.x(), startPoint.y())

    self.rubberBand.addPoint(point1, False)
    self.rubberBand.addPoint(point2, False)
    self.rubberBand.addPoint(point3, False)
    self.rubberBand.addPoint(point4, True)	# true to update canvas
    self.rubberBand.show()

  def rectangle(self):
    if self.startPoint == None or self.endPoint == None:
      return None
    #elif self.startPoint.x() == self.endPoint.x() or self.startPoint.y() == self.endPoint.y():
    #  return None

    return QgsRectangle(self.startPoint, self.endPoint)

  def setRectangle(self, rect):
    if rect == self.rectangle():
      return False

    if rect == None:
      self.reset()
    else:
      self.startPoint = QgsPoint(rect.xMaximum(), rect.yMaximum())
      self.endPoint = QgsPoint(rect.xMinimum(), rect.yMinimum())
      self.showRect(self.startPoint, self.endPoint)
    return True
