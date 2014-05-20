# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                             -------------------
        begin                : 2014-03-27
        copyright            : (C) 2014 Minoru Akagi
        email                : akaginch@gmail.com
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
from PyQt4.QtCore import Qt, qDebug, SIGNAL, QDir, QSettings #QVariant
from PyQt4.QtGui import *       #, QColor, QColorDialog, QFileDialog, QMessageBox
from qgis.core import *
import os

from ui.ui_worldproperties import Ui_WorldPropertiesWidget
from ui.ui_controlsproperties import Ui_ControlsPropertiesWidget
from ui.ui_demproperties import Ui_DEMPropertiesWidget
from ui.ui_vectorproperties import Ui_VectorPropertiesWidget

from qgis2threejsmain import MapTo3D, ObjectTreeItem
from stylewidget import StyleWidget
from quadtree import QuadTree
import qgis2threejstools as tools

PAGE_NONE = 0
PAGE_WORLD = 1
PAGE_CONTROLS = 2
PAGE_DEM = 3
PAGE_VECTOR = 4

def is_number(val):
  try:
    float(val)
    return True
  except:
    return False

class PropertyPage(QWidget):

  def __init__(self, pageType, dialog, parent=None):
    QWidget.__init__(self, parent)
    self.pageType = pageType
    self.dialog = dialog
    self.propertyWidgets = []
    self.defaultProperties = {}

  def itemChanged(self, item):
    pass

  def setLayoutVisible(self, layout, visible):
    for i in range(layout.count()):
      item = layout.itemAt(i)
      w = item.widget()
      if w is not None:
        w.setVisible(visible)
        continue
      l = item.layout()
      if l is not None:
        self.setLayoutVisible(l, visible)

  def setLayoutsVisible(self, layouts, visible):
    for layout in layouts:
      self.setLayoutVisible(layout, visible)

  def setWidgetsVisible(self, widgets, visible):
    for w in widgets:
      w.setVisible(visible)

  def setLayoutEnabled(self, layout, enabled):
    for i in range(layout.count()):
      item = layout.itemAt(i)
      w = item.widget()
      if w is not None:
        w.setEnabled(enabled)
        continue
      l = item.layout()
      if l is not None:
        self.setLayoutEnabled(l, enabled)

  def setLayoutsEnabled(self, layouts, enabled):
    for layout in layouts:
      self.setLayoutEnabled(layout, enabled)

  def setPropertyWidgets(self, widgets):
    self.propertyWidgets = widgets
    # save default properties
    self.defaultProperties = self.properties()

  def properties(self):
    p = {}
    for w in self.propertyWidgets:
      v = None
      if isinstance(w, QComboBox):
        index = w.currentIndex()
        if index == -1:
          v = None
        else:
          v = w.itemData(index)
      elif isinstance(w, QRadioButton):
        if not w.isChecked():
          continue
        v = w.isChecked()
      elif isinstance(w, QCheckBox):
        v = w.isChecked()
      elif isinstance(w, (QSlider, QSpinBox)):
        v = w.value()
      elif isinstance(w, QLineEdit):
        v = w.text()
      elif isinstance(w, StyleWidget):
        v = w.values()
      else:   #TODO
        QMessageBox.information(None, "propertypages.py", "Not recognized widget type: " + str(type(w)))

      p[w.objectName()] = v
    return p

  def setProperties(self, properties):
    for n, v in properties.items():
      w = getattr(self, n, None)
      if w is None:
        continue
      if isinstance(w, QComboBox):
        if v is not None:
          index = w.findData(v)
          if index != -1:
            w.setCurrentIndex(index)
      elif isinstance(w, (QRadioButton, QCheckBox)): # subclass of QAbstractButton
        w.setChecked(v)
      elif isinstance(w, (QSlider, QSpinBox)):
        w.setValue(v)
      elif isinstance(w, QLineEdit):
        w.setText(v)
      elif isinstance(w, StyleWidget):
        if len(v):
          w.setValues(v)
      else:     #TODO
        QMessageBox.information(None, "propertypages.py", "Cannot restore %s property" % n)

class WorldPropertyPage(PropertyPage, Ui_WorldPropertiesWidget):

  def __init__(self, dialog, parent=None):
    PropertyPage.__init__(self, PAGE_WORLD, dialog, parent)
    Ui_WorldPropertiesWidget.setupUi(self, self)

    self.setPropertyWidgets([self.lineEdit_zFactor, self.lineEdit_zShift, self.radioButton_Color, self.lineEdit_Color])
    self.radioButton_Color.toggled.connect(self.backgroundToggled)
    self.toolButton_Color.clicked.connect(self.colorButtonClicked)

  def setup(self, properties=None):
    canvas = self.dialog.iface.mapCanvas()
    extent = canvas.extent()
    outsize = canvas.mapSettings().outputSize() if QGis.QGIS_VERSION_INT >= 20300 else canvas.mapRenderer()

    self.lineEdit_MapCanvasExtent.setText("%.4f, %.4f - %.4f, %.4f" % (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()))
    self.lineEdit_MapCanvasSize.setText("{0} x {1}".format(outsize.width(), outsize.height()))

    # restore properties
    if properties:
      PropertyPage.setProperties(self, properties)

  def backgroundToggled(self, checked):
    isColor = self.radioButton_Color.isChecked()
    self.lineEdit_Color.setEnabled(isColor)
    self.toolButton_Color.setEnabled(isColor)

  def colorButtonClicked(self):
    color = QColorDialog.getColor(QColor(self.lineEdit_Color.text().replace("0x", "#")))
    if color.isValid():
      self.lineEdit_Color.setText(color.name().replace("#", "0x"))

  def properties(self):
    p = PropertyPage.properties(self)
    # check validity
    if not is_number(self.lineEdit_zFactor.text()):
      p["lineEdit_zFactor"] = "1.5"
    if not is_number(self.lineEdit_zShift.text()):
      p["lineEdit_zShift"] = "0"
    return p

class ControlsPropertyPage(PropertyPage, Ui_ControlsPropertiesWidget):

  def __init__(self, dialog, parent=None):
    PropertyPage.__init__(self, PAGE_CONTROLS, dialog, parent)
    Ui_ControlsPropertiesWidget.setupUi(self, self)

    self.controlsDir = os.path.join(tools.pluginDir(), "js", "threejs", "controls")

    self.initControlsList()
    self.setPropertyWidgets([self.comboBox_Controls])

    self.comboBox_Controls.currentIndexChanged.connect(self.controlsChanged)

  def setup(self, properties=None):
    # restore properties
    comboBox = self.comboBox_Controls
    comboBox.blockSignals(True)
    if properties:
      PropertyPage.setProperties(self, properties)
    else:
      controls = QSettings().value("/Qgis2threejs/lastControls", "TrackballControls.js", type=unicode)
      index = comboBox.findText(controls)
      if index != -1:
        comboBox.setCurrentIndex(index)
    comboBox.blockSignals(False)

    self.controlsChanged(comboBox.currentIndex())

  def initControlsList(self):
    # list controls
    self.comboBox_Controls.clear()
    for entry in QDir(self.controlsDir).entryList(["*.js"]):
      self.comboBox_Controls.addItem(entry, entry)

  def controlsChanged(self, index):
    controls = self.comboBox_Controls.itemText(index)
    descFile = os.path.splitext(os.path.join(self.controlsDir, controls))[0] + ".txt"
    if os.path.exists(descFile):
      with open(descFile) as f:
        desc = f.read()
    else:
      desc = "No description"
    self.textEdit.setText(desc)

class DEMPropertyPage(PropertyPage, Ui_DEMPropertiesWidget):

  def __init__(self, dialog, parent=None):
    PropertyPage.__init__(self, PAGE_DEM, dialog, parent)
    Ui_DEMPropertiesWidget.setupUi(self, self)

    # set read only to line edits of spin boxes
    self.spinBox_Size.findChild(QLineEdit).setReadOnly(True)
    self.spinBox_Roughening.findChild(QLineEdit).setReadOnly(True)

    self.isPrimary = False
    self.layer = None
    self.demWidth = self.demHeight = 0

    dispTypeButtons = [self.radioButton_MapCanvas, self.radioButton_ImageFile, self.radioButton_SolidColor, self.radioButton_Wireframe]
    widgets = [self.comboBox_DEMLayer, self.spinBox_demtransp, self.spinBox_sidetransp]
    widgets += [self.radioButton_Simple, self.horizontalSlider_Resolution]
    widgets += [self.checkBox_Surroundings, self.spinBox_Size, self.spinBox_Roughening]
    widgets += [self.radioButton_Advanced, self.spinBox_Height, self.lineEdit_xmin, self.lineEdit_ymin, self.lineEdit_xmax, self.lineEdit_ymax]
    widgets += dispTypeButtons
    widgets += [self.lineEdit_ImageFile, self.lineEdit_Color]
    widgets += [self.checkBox_Sides, self.checkBox_Frame]
    self.setPropertyWidgets(widgets)

    self.initDEMLayerList()

    self.comboBox_DEMLayer.currentIndexChanged.connect(self.demLayerChanged)
    self.horizontalSlider_Resolution.valueChanged.connect(self.calculateResolution)
    self.radioButton_Simple.toggled.connect(self.samplingModeChanged)
    self.checkBox_Surroundings.toggled.connect(self.surroundingsToggled)
    self.spinBox_Roughening.valueChanged.connect(self.rougheningChanged)
    self.spinBox_Height.valueChanged.connect(self.updateQuads)
    for radioButton in dispTypeButtons:
      radioButton.toggled.connect(self.dispTypeChanged)
    self.toolButton_ImageFile.clicked.connect(self.browseClicked)
    self.toolButton_Color.clicked.connect(self.colorButtonClicked)
    self.checkBox_Sides.toggled.connect(self.sidesToggled)

    self.toolButton_PointTool.clicked.connect(dialog.startPointSelection)

  def setup(self, properties=None, layer=None, isPrimary=True):
    self.isPrimary = isPrimary
    self.layer = layer

    self.setLayoutsVisible([self.formLayout_DEMLayer, self.verticalLayout_Advanced, self.formLayout_Surroundings], isPrimary)
    self.setWidgetsVisible([self.radioButton_Advanced, self.groupBox_Accessories], isPrimary)
    self.setWidgetsVisible([self.toolButton_PointTool], False)
    self.setEnabled(isPrimary or self.dialog.currentItem.data(0, Qt.CheckStateRole) == Qt.Checked)

    # select dem layer
    layerId = None
    if layer is not None:
      layerId = layer.id()

    self.comboBox_DEMLayer.blockSignals(True)
    currentIndex = self.selectDEMLayer(layerId)
    self.comboBox_DEMLayer.blockSignals(False)
    self.groupBox_Resampling.setEnabled(True)
    self.demLayerChanged(currentIndex)

    # restore properties for the layer
    if properties:
      PropertyPage.setProperties(self, properties)
    else:
      PropertyPage.setProperties(self, self.defaultProperties)

    self.calculateResolution()

    # set enablement and visibility of widgets
    if isPrimary:
      self.samplingModeChanged(True)
      self.surroundingsToggled(self.checkBox_Surroundings.isChecked())
    self.dispTypeChanged()

    if isPrimary:
      # enable map tool to select focus area
      self.connect(self.dialog.mapTool, SIGNAL("rectangleCreated()"), self.rectangleSelected)
      self.dialog.startPointSelection()
    else:
      self.checkBox_Sides.setChecked(False)   # no sides with additional dem

  def initDEMLayerList(self):
    comboBox = self.comboBox_DEMLayer
    # list 1 band raster layers
    comboBox.clear()
    comboBox.addItem("Flat plane (no DEM used)", 0)
    for id, layer in QgsMapLayerRegistry().instance().mapLayers().items():
      if layer.type() == QgsMapLayer.RasterLayer and layer.providerType() == "gdal" and layer.bandCount() == 1:
        comboBox.addItem(layer.name(), id)

  def selectDEMLayer(self, layerId=None):
    comboBox = self.comboBox_DEMLayer
    if layerId is not None:
      # select the last selected layer
      index = comboBox.findData(layerId)
      if index != -1:
        comboBox.setCurrentIndex(index)
      return index
    elif comboBox.count() > 1:
      # select the first 1 band raster layer
      comboBox.setCurrentIndex(1)
      return 1
    # combo box has one item "(Flat plane)"
    return 0

  def demLayerChanged(self, index):
    if not self.isPrimary:
      return
    comboBox = self.comboBox_DEMLayer
    useDEM = comboBox.itemData(index) != 0
    self.groupBox_Resampling.setEnabled(useDEM)
    if not useDEM:
      self.checkBox_Surroundings.setChecked(False)
    self.dialog.primaryDEMChanged(comboBox.itemData(index))

  def itemChanged(self, item):
    if not self.isPrimary:
      self.setEnabled(item.data(0, Qt.CheckStateRole) == Qt.Checked)

  def browseClicked(self):
    directory = os.path.split(self.lineEdit_ImageFile.text())[0]
    if directory == "":
      directory = QDir.homePath()
    filename = QFileDialog.getOpenFileName(self, "Select image file", directory, "Images (*.png *.jpeg *.jpg *.tif *.gif *.bmp);;All files (*.*)")
    if filename:
      self.lineEdit_ImageFile.setText(filename)

  def colorButtonClicked(self):
    color = QColorDialog.getColor(QColor(self.lineEdit_Color.text().replace("0x", "#")))
    if color.isValid():
      self.lineEdit_Color.setText(color.name().replace("#", "0x"))

  def surroundingsToggled(self, checked):
    self.calculateResolution()
    self.setLayoutEnabled(self.horizontalLayout_Surroundings, checked)
    self.radioButton_ImageFile.setEnabled(not checked)
    self.groupBox_Accessories.setEnabled(not checked)

    if checked and self.radioButton_ImageFile.isChecked():
      self.radioButton_MapCanvas.setChecked(True)

  def rougheningChanged(self, v):
    self.calculateResolution()
    # possible value is a power of 2
    self.spinBox_Roughening.setSingleStep(v)
    self.spinBox_Roughening.setMinimum(max(v / 2, 1))

  def sidesToggled(self, checked):
    self.label_sidetransp.setEnabled(checked)
    self.spinBox_sidetransp.setEnabled(checked)

  def hide(self):
    PropertyPage.hide(self)
    if self.isPrimary:
      self.disconnect(self.dialog.mapTool, SIGNAL("rectangleCreated()"), self.rectangleSelected)
      self.dialog.endPointSelection()

  def calculateResolution(self, v=None):
    canvas = self.dialog.iface.mapCanvas()
    size = 100 * self.horizontalSlider_Resolution.value()

    # calculate resolution and size
    outsize = canvas.mapSettings().outputSize() if QGis.QGIS_VERSION_INT >= 20300 else canvas.mapRenderer()
    width, height = outsize.width(), outsize.height()
    s = (size * size / float(width * height)) ** 0.5
    if s < 1:
      width = int(width * s)
      height = int(height * s)

    if self.checkBox_Surroundings.isChecked():
      roughening = self.spinBox_Roughening.value()
      if width % roughening != 0:
        width = int(float(width) / roughening + 0.9) * roughening
      if height % roughening != 0:
        height = int(float(height) / roughening + 0.9) * roughening

    self.demWidth = width + 1
    self.demHeight = height + 1
    self.label_Resolution.setText("{0} x {1} px".format(self.demWidth, self.demHeight))

    extent = canvas.extent()
    xres = extent.width() / width
    yres = extent.height() / height
    self.lineEdit_HRes.setText(str(xres))
    self.lineEdit_VRes.setText(str(yres))

  def properties(self):
    p = PropertyPage.properties(self)
    item = self.dialog.currentItem
    if item is not None:
      p["visible"] = item.data(0, Qt.CheckStateRole) == Qt.Checked
    p["dem_Width"] = self.demWidth
    p["dem_Height"] = self.demHeight
    return p

  def updateQuads(self, v=None):
    isValid = True
    try:
      c = map(float, [self.lineEdit_xmin.text(), self.lineEdit_ymin.text(), self.lineEdit_xmax.text(), self.lineEdit_ymax.text()])
    except:
      isValid = False

    if isValid:
      # create quad rubber bands
      rect = QgsRectangle(c[0], c[1], c[2], c[3])
      quadtree = QuadTree(self.dialog.iface.mapCanvas().extent())
      quadtree.buildTreeByRect(rect, self.spinBox_Height.value())
      self.dialog.createRubberBands(quadtree.quads(), rect.center())
      self.dialog.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
    else:
      self.dialog.clearRubberBands()

  def rectangleSelected(self):
    self.radioButton_Advanced.setChecked(True)
    rect = self.dialog.mapTool.rectangle()
    toRect = rect.width() and rect.height()
    self.switchFocusMode(toRect)
    self.lineEdit_xmin.setText(str(rect.xMinimum()))
    self.lineEdit_ymin.setText(str(rect.yMinimum()))
    self.lineEdit_xmax.setText(str(rect.xMaximum()))
    self.lineEdit_ymax.setText(str(rect.yMaximum()))

    # update quad rubber bands
    self.updateQuads()

  def dispTypeChanged(self, checked=True):
    if checked:
      enabled = self.radioButton_ImageFile.isChecked()
      self.lineEdit_ImageFile.setEnabled(enabled)
      self.toolButton_ImageFile.setEnabled(enabled)

      enabled = self.radioButton_SolidColor.isChecked() or self.radioButton_Wireframe.isChecked()
      self.lineEdit_Color.setEnabled(enabled)
      self.toolButton_Color.setEnabled(enabled)

  def samplingModeChanged(self, checked):
    isSimpleMode = self.radioButton_Simple.isChecked()
    self.setLayoutsEnabled([self.verticalLayout_Simple, self.horizontalLayout_ImageFile], isSimpleMode)
    self.setLayoutsEnabled([self.horizontalLayout_Surroundings], isSimpleMode and self.checkBox_Surroundings.isChecked())
    isAdvancedMode = not isSimpleMode

    if self.isPrimary:
      self.setWidgetsVisible([self.groupBox_Accessories], isSimpleMode)
      self.setLayoutsVisible([self.horizontalLayout_Advanced1, self.horizontalLayout_Advanced3], isAdvancedMode)
      self.setWidgetsVisible([self.label_Focus], isAdvancedMode)
      if isSimpleMode:
        self.setLayoutVisible(self.horizontalLayout_Advanced4, False)
      else:
        isPoint = (self.lineEdit_xmin.text() == self.lineEdit_xmax.text() and self.lineEdit_ymin.text() == self.lineEdit_ymax.text())
        self.switchFocusMode(not isPoint)

    if isAdvancedMode and self.radioButton_ImageFile.isChecked():
      self.radioButton_MapCanvas.setChecked(True)

  def switchFocusMode(self, toRect):
    toPoint = not toRect
    self.setLayoutVisible(self.horizontalLayout_Advanced4, toRect)

    suffix = "max" if toRect else ""
    self.label_xmax.setText("x" + suffix)
    self.label_ymax.setText("y" + suffix)
    selection = "area" if toRect else "point"
    action = "Stroke a rectangle" if toRect else "Click"
    self.label_Focus.setText("Focus {0} ({1} on map canvas to set values)".format(selection, action))

class VectorPropertyPage(PropertyPage, Ui_VectorPropertiesWidget):

  def __init__(self, dialog, parent=None):
    PropertyPage.__init__(self, PAGE_VECTOR, dialog, parent)
    Ui_VectorPropertiesWidget.setupUi(self, self)

    self.layer = None

    # initialize vector style widgets
    self.heightWidget = StyleWidget(StyleWidget.HEIGHT)
    self.heightWidget.setObjectName("heightWidget")
    self.verticalLayout_zCoordinate.addWidget(self.heightWidget)
    self.colorWidget = StyleWidget(StyleWidget.COLOR)
    self.colorWidget.setObjectName("colorWidget")
    self.verticalLayout_Styles.addWidget(self.colorWidget)
    self.transparencyWidget = StyleWidget(StyleWidget.TRANSPARENCY)
    self.transparencyWidget.setObjectName("transparencyWidget")
    self.verticalLayout_Styles.addWidget(self.transparencyWidget)
    self.labelHeightWidget = StyleWidget(StyleWidget.LABEL_HEIGHT)
    self.labelHeightWidget.setObjectName("labelHeightWidget")
    self.verticalLayout_Label.addWidget(self.labelHeightWidget)
    self.labelHeightWidget.setEnabled(False)

    self.STYLE_MAX_COUNT = dialog.STYLE_MAX_COUNT
    self.styleWidgets = []
    for i in range(self.STYLE_MAX_COUNT):
      objName = "styleWidget" + str(i)

      widget = StyleWidget()
      widget.setVisible(False)
      widget.setObjectName(objName)
      self.styleWidgets.append(widget)
      self.verticalLayout_Styles.addWidget(widget)

      # assign the widget to property page attribute
      setattr(self, objName, widget)

    widgets = [self.comboBox_ObjectType, self.heightWidget, self.colorWidget, self.transparencyWidget] + self.styleWidgets
    widgets += [self.checkBox_ExportAttrs, self.comboBox_Label, self.labelHeightWidget]
    self.setPropertyWidgets(widgets)

    self.comboBox_ObjectType.currentIndexChanged.connect(self.objectTypeChanged)
    self.checkBox_ExportAttrs.toggled.connect(self.exportAttrsToggled)

  def setup(self, properties=None, layer=None):
    self.layer = layer

    self.setEnabled(self.dialog.currentItem.data(0, Qt.CheckStateRole) == Qt.Checked)
    for i in range(self.STYLE_MAX_COUNT):
      self.styleWidgets[i].hide()

    obj_types = self.dialog.objectTypeManager.objectTypeNames(layer.geometryType())

    # set up object type combo box
    self.comboBox_ObjectType.blockSignals(True)
    self.comboBox_ObjectType.clear()
    for index, obj_type in enumerate(obj_types):
      self.comboBox_ObjectType.addItem(obj_type, index)
    if properties:
      # restore object type selection
      self.comboBox_ObjectType.setCurrentIndex(properties.get("comboBox_ObjectType", 0))
    self.comboBox_ObjectType.blockSignals(False)

    # create MapTo3d object to calculate default values
    world = self.dialog.properties[ObjectTreeItem.ITEM_WORLD] or {}
    ve = float(world.get("lineEdit_zFactor", 1.5))
    vs = float(world.get("lineEdit_zShift", 0))
    mapTo3d = MapTo3D(self.dialog.iface.mapCanvas(), verticalExaggeration=ve, verticalShift=vs)

    # set up height widget and label height widget
    self.heightWidget.setup(layer=layer)
    if layer.geometryType() != QGis.Line:
      defaultLabelHeight = 5
      self.labelHeightWidget.setup(layer=layer, defaultValue=defaultLabelHeight/mapTo3d.multiplierZ)
    else:
      self.labelHeightWidget.hide()

    # set up style widgets for selected object type
    self.objectTypeChanged()

    # set up label combo box
    hasPoint = (layer.geometryType() in (QGis.Point, QGis.Polygon))
    self.setLayoutVisible(self.formLayout_Label, hasPoint)
    self.comboBox_Label.clear()
    if hasPoint:
      self.comboBox_Label.addItem("(No label)")
      fields = self.layer.pendingFields()
      for i in range(fields.count()):
        self.comboBox_Label.addItem(fields[i].name(), i)

    # restore other properties for the layer
    if properties:
      PropertyPage.setProperties(self, properties)
    else:
      PropertyPage.setProperties(self, self.defaultProperties)

  def objectTypeChanged(self, idx=None):
    # notice JSON model is experimental
    self.label_ObjectTypeMessage.setVisible(self.comboBox_ObjectType.currentText() == "JSON model")

    # create MapTo3d object to calculate default values
    world = self.dialog.properties[ObjectTreeItem.ITEM_WORLD] or {}
    ve = float(world.get("lineEdit_zFactor", 1.5))
    vs = float(world.get("lineEdit_zShift", 0))
    mapTo3d = MapTo3D(self.dialog.iface.mapCanvas(), verticalExaggeration=ve, verticalShift=vs)

    # setup widgets
    self.dialog.objectTypeManager.setupForm(self, mapTo3d, self.layer, self.layer.geometryType(), self.comboBox_ObjectType.currentIndex())

  def itemChanged(self, item):
    self.setEnabled(item.data(0, Qt.CheckStateRole) == Qt.Checked)

  def exportAttrsToggled(self, checked):
    self.setLayoutEnabled(self.formLayout_Label, checked)
    self.labelHeightWidget.setEnabled(checked)

  def properties(self):
    p = PropertyPage.properties(self)
    item = self.dialog.currentItem
    if item is not None:
      p["visible"] = item.data(0, Qt.CheckStateRole) == Qt.Checked
    return p
