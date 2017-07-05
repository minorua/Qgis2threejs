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
import os
import re

from PyQt5.QtCore import Qt, QDir, QSettings, QPoint
from PyQt5.QtWidgets import QCheckBox, QColorDialog, QComboBox, QFileDialog, QLineEdit, QRadioButton, QSlider, QSpinBox, QToolTip, QWidget
from PyQt5.QtGui import QColor
from qgis.core import QgsFieldProxyModel, QgsMapLayer, QgsWkbTypes
from qgis.gui import QgsFieldExpressionWidget

from .ui.worldproperties import Ui_WorldPropertiesWidget
from .ui.controlsproperties import Ui_ControlsPropertiesWidget
from .ui.demproperties import Ui_DEMPropertiesWidget
from .ui.vectorproperties import Ui_VectorPropertiesWidget

from .conf import def_vals
from .qgis2threejscore import calculateDEMSize, createQuadTree
from .qgis2threejstools import getLayersInProject, logMessage
from .rotatedrect import RotatedRect
from .stylewidget import StyleWidget
from . import qgis2threejstools as tools
from .vectorobject import objectTypeManager

PAGE_NONE = 0
PAGE_WORLD = 1
PAGE_CONTROLS = 2
PAGE_DEM = 3
PAGE_VECTOR = 4


def is_number(val):
  try:
    float(val)
    return True
  except ValueError:
    return False


class PropertyPage(QWidget):

  def __init__(self, pageType, dialog, parent=None):
    QWidget.__init__(self, parent)
    self.pageType = pageType
    self.dialog = dialog
    self.propertyWidgets = []

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

  def setWidgetsEnabled(self, widgets, enabled):
    for w in widgets:
      w.setEnabled(enabled)

  def registerPropertyWidgets(self, widgets):
    self.propertyWidgets = widgets

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
      elif isinstance(w, QgsFieldExpressionWidget):
        v = w.expression()
      else:
        logMessage("[propertypages.py] Not recognized widget type: " + str(type(w)))

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
      elif isinstance(w, (QRadioButton, QCheckBox)):  # subclass of QAbstractButton
        w.setChecked(v)
      elif isinstance(w, (QSlider, QSpinBox)):
        w.setValue(v)
      elif isinstance(w, QLineEdit):
        w.setText(v)
      elif isinstance(w, StyleWidget):
        if len(v):
          w.setValues(v)
      elif isinstance(w, QgsFieldExpressionWidget):
        w.setExpression(v)
      else:
        logMessage("[propertypages.py] Cannot restore %s property" % n)


class WorldPropertyPage(PropertyPage, Ui_WorldPropertiesWidget):

  def __init__(self, dialog, parent=None):
    PropertyPage.__init__(self, PAGE_WORLD, dialog, parent)
    Ui_WorldPropertiesWidget.setupUi(self, self)

    self.registerPropertyWidgets([self.lineEdit_BaseSize, self.lineEdit_zFactor, self.lineEdit_zShift, self.radioButton_Color, self.lineEdit_Color, self.radioButton_WGS84])
    self.toolButton_Color.clicked.connect(self.colorButtonClicked)

  def setup(self, properties=None):
    canvas = self.dialog.iface.mapCanvas()
    extent = canvas.extent()
    outsize = canvas.mapSettings().outputSize()

    self.lineEdit_MapCanvasExtent.setText("%.4f, %.4f - %.4f, %.4f" % (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()))
    self.lineEdit_MapCanvasSize.setText("{0} x {1}".format(outsize.width(), outsize.height()))

    # restore properties
    if properties:
      self.setProperties(properties)
    else:
      self.lineEdit_BaseSize.setText(str(def_vals.baseSize))
      self.lineEdit_zFactor.setText(str(def_vals.zExaggeration))
      self.lineEdit_zShift.setText(str(def_vals.zShift))

    # Supported projections
    # https://github.com/proj4js/proj4js
    projs = ["longlat", "merc"]
    projs += ["aea", "aeqd", "cass", "cea", "eqc", "eqdc", "gnom", "krovak", "laea", "lcc", "mill", "moll",
              "nzmg", "omerc", "poly", "sinu", "somerc", "stere", "sterea", "tmerc", "utm", "vandg"]

    mapSettings = canvas.mapSettings()
    proj = mapSettings.destinationCrs().toProj4()
    m = re.search("\+proj=(\w+)", proj)
    proj_supported = bool(m and m.group(1) in projs)

    if not proj_supported:
      self.radioButton_ProjectCRS.setChecked(True)
    self.radioButton_WGS84.setEnabled(proj_supported)

  def colorButtonClicked(self):
    color = QColorDialog.getColor(QColor(self.lineEdit_Color.text().replace("0x", "#")))
    if color.isValid():
      self.lineEdit_Color.setText(color.name().replace("#", "0x"))

  def properties(self):
    p = PropertyPage.properties(self)
    # check validity
    if not is_number(self.lineEdit_BaseSize.text()):
      p["lineEdit_BaseSize"] = str(def_vals.baseSize)
    if not is_number(self.lineEdit_zFactor.text()):
      p["lineEdit_zFactor"] = str(def_vals.zExaggeration)
    if not is_number(self.lineEdit_zShift.text()):
      p["lineEdit_zShift"] = str(def_vals.zShift)
    return p


class ControlsPropertyPage(PropertyPage, Ui_ControlsPropertiesWidget):

  def __init__(self, dialog, parent=None):
    PropertyPage.__init__(self, PAGE_CONTROLS, dialog, parent)
    Ui_ControlsPropertiesWidget.setupUi(self, self)

    self.controlsDir = os.path.join(tools.pluginDir(), "js", "threejs", "controls")

    self.initControlsList()
    self.registerPropertyWidgets([self.comboBox_Controls])

    self.comboBox_Controls.currentIndexChanged.connect(self.controlsChanged)

  def setup(self, properties=None):
    # restore properties
    comboBox = self.comboBox_Controls
    comboBox.blockSignals(True)
    if properties:
      self.setProperties(properties)
    else:
      controls = QSettings().value("/Qgis2threejs/lastControls", def_vals.controls, type=str)
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

  def __init__(self, dialog, parent=None):      #TODO: dialog -> canvas, dialog
    PropertyPage.__init__(self, PAGE_DEM, dialog, parent)
    Ui_DEMPropertiesWidget.setupUi(self, self)

    # set read only to line edits of spin boxes
    self.spinBox_Size.findChild(QLineEdit).setReadOnly(True)
    self.spinBox_Roughening.findChild(QLineEdit).setReadOnly(True)

    self.isPrimary = False
    self.layer = None
    self.layerImageIds = []

    dispTypeButtons = [self.radioButton_MapCanvas, self.radioButton_LayerImage, self.radioButton_ImageFile, self.radioButton_SolidColor]
    widgets = [self.comboBox_DEMLayer, self.spinBox_Opacity]
    widgets += [self.radioButton_Simple, self.horizontalSlider_DEMSize]
    widgets += [self.checkBox_Surroundings, self.spinBox_Size, self.spinBox_Roughening]
    widgets += [self.radioButton_Advanced, self.spinBox_Height, self.lineEdit_centerX, self.lineEdit_centerY, self.lineEdit_rectWidth, self.lineEdit_rectHeight]
    widgets += dispTypeButtons
    widgets += [self.checkBox_TransparentBackground, self.lineEdit_ImageFile, self.lineEdit_Color, self.comboBox_TextureSize, self.checkBox_Shading]
    widgets += [self.checkBox_Clip, self.comboBox_ClipLayer]
    widgets += [self.checkBox_Sides, self.checkBox_Frame]
    self.registerPropertyWidgets(widgets)

    self.initLayerComboBox()
    self.initTextureSizeComboBox()

    self.comboBox_DEMLayer.currentIndexChanged.connect(self.demLayerChanged)
    self.horizontalSlider_DEMSize.valueChanged.connect(self.resolutionSliderChanged)
    self.radioButton_Simple.toggled.connect(self.samplingModeChanged)
    self.checkBox_Surroundings.toggled.connect(self.surroundingsToggled)
    self.spinBox_Roughening.valueChanged.connect(self.rougheningChanged)
    self.spinBox_Height.valueChanged.connect(self.updateQuads)
    for radioButton in dispTypeButtons:
      radioButton.toggled.connect(self.dispTypeChanged)
    self.toolButton_SelectLayer.clicked.connect(self.selectLayerClicked)
    self.toolButton_ImageFile.clicked.connect(self.browseClicked)
    self.toolButton_Color.clicked.connect(self.colorButtonClicked)

    self.toolButton_PointTool.clicked.connect(dialog.startPointSelection)

  def setup(self, properties=None, layer=None, isPrimary=True):
    self.isPrimary = isPrimary
    self.layer = layer

    self.setLayoutsVisible([self.formLayout_DEMLayer, self.verticalLayout_Advanced, self.formLayout_Surroundings], isPrimary)
    self.setWidgetsVisible([self.radioButton_Advanced], isPrimary)
    self.setWidgetsVisible([self.toolButton_PointTool], False)
    if self.dialog.currentItem:
      self.setEnabled(isPrimary or self.dialog.currentItem.data(0, Qt.CheckStateRole) == Qt.Checked)
    else:
      self.setEnabled(True)

    # select dem layer
    layerId = None
    if layer is not None:
      layerId = layer.id()

    self.comboBox_DEMLayer.blockSignals(True)
    currentIndex = self.selectDEMLayer(layerId)
    self.comboBox_DEMLayer.blockSignals(False)
    self.groupBox_Resampling.setEnabled(True)
    self.demLayerChanged(currentIndex)

    # use default properties if properties is not set
    if not properties:
      properties = self.properties()
      properties["comboBox_TextureSize"] = 100
      properties["checkBox_Sides"] = self.isPrimary

    # restore properties of the layer
    self.spinBox_Height.blockSignals(True)
    self.setProperties(properties)
    self.spinBox_Height.blockSignals(False)

    self.updateDEMSize()
    self.updateLayerImageLabel()

    # set enablement and visibility of widgets
    if isPrimary:
      self.samplingModeChanged(True)
      self.surroundingsToggled(self.checkBox_Surroundings.isChecked())
    self.dispTypeChanged()

    if isPrimary:
      # enable map tool to select focus area
      #self.connect(self.dialog.mapTool, SIGNAL("rectangleCreated()"), self.rectangleSelected)    #TODO: new style
      self.dialog.startPointSelection()
    else:
      pass
      #TODO: remove
      #self.checkBox_Sides.setChecked(False)   # no sides with additional dem

  def initLayerComboBox(self):
    # list of 1 band raster layers and plugin dem providers
    comboDEM = self.comboBox_DEMLayer
    comboDEM.clear()
    comboDEM.addItem("Flat plane (no DEM used)", 0)

    # plugin dem providers
    if self.dialog.pluginManager:
      for plugin in self.dialog.pluginManager.demProviderPlugins():
        comboDEM.addItem(plugin.providerName(), "plugin:" + plugin.providerId())

    # list of polygon layers
    comboPolygon = self.comboBox_ClipLayer
    comboPolygon.clear()

    for layer in getLayersInProject():
      if layer.type() == QgsMapLayer.RasterLayer:
        if layer.providerType() == "gdal" and layer.bandCount() == 1:
          comboDEM.addItem(layer.name(), layer.id())
      elif layer.type() == QgsMapLayer.VectorLayer:
        if layer.geometryType() == QgsWkbTypes.PolygonGeometry:
          comboPolygon.addItem(layer.name(), layer.id())

  def initTextureSizeComboBox(self):
    canvas = self.dialog.iface.mapCanvas()
    outsize = canvas.mapSettings().outputSize()

    self.comboBox_TextureSize.clear()
    for i in [4, 2, 1]:
      percent = i * 100
      text = "{0} %  ({1} x {2} px)".format(percent, outsize.width() * i, outsize.height() * i)
      self.comboBox_TextureSize.addItem(text, percent)

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

  def resolutionSliderChanged(self, v):
    self.updateDEMSize()
    size = 100 * self.horizontalSlider_DEMSize.value()
    QToolTip.showText(self.horizontalSlider_DEMSize.mapToGlobal(QPoint(0, 0)), "about {0} x {0}".format(size), self.horizontalSlider_DEMSize)

  def itemChanged(self, item):
    if not self.isPrimary:
      self.setEnabled(item.data(0, Qt.CheckStateRole) == Qt.Checked)

  def selectLayerClicked(self):
    from .layerselectdialog import LayerSelectDialog
    dialog = LayerSelectDialog(self)
    dialog.initTree(self.layerImageIds)
    dialog.setMapSettings(self.dialog.iface.mapCanvas().mapSettings())
    if not dialog.exec_():
      return

    layers = dialog.visibleLayers()
    self.layerImageIds = [layer.id() for layer in layers]
    self.updateLayerImageLabel()

  def updateLayerImageLabel(self):
    self.label_LayerImage.setText(tools.shortTextFromSelectedLayerIds(self.layerImageIds))

  def browseClicked(self):
    directory = os.path.split(self.lineEdit_ImageFile.text())[0]
    if directory == "":
      directory = QDir.homePath()
    filterString = "Images (*.png *.jpg *.gif *.bmp);;All files (*.*)"
    filename, _ = QFileDialog.getOpenFileName(self, "Select image file", directory, filterString)
    if filename:
      self.lineEdit_ImageFile.setText(filename)

  def colorButtonClicked(self):
    color = QColorDialog.getColor(QColor(self.lineEdit_Color.text().replace("0x", "#")))
    if color.isValid():
      self.lineEdit_Color.setText(color.name().replace("#", "0x"))

  def surroundingsToggled(self, checked):
    self.updateDEMSize()
    self.setLayoutEnabled(self.gridLayout_Surroundings, checked)

    is_simple = self.radioButton_Simple.isChecked()
    is_simple_wo_surroundings = is_simple and not checked
    self.setWidgetsEnabled([self.radioButton_ImageFile, self.groupBox_Clip], is_simple_wo_surroundings)

    if checked and self.radioButton_ImageFile.isChecked():
      self.radioButton_MapCanvas.setChecked(True)

  def rougheningChanged(self, v):
    self.updateDEMSize()
    # possible value is a power of 2
    self.spinBox_Roughening.setSingleStep(v)
    self.spinBox_Roughening.setMinimum(max(v // 2, 1))

  def hide(self):
    PropertyPage.hide(self)
    if self.isPrimary:
      #self.disconnect(self.dialog.mapTool, SIGNAL("rectangleCreated()"), self.rectangleSelected)   #TODO: new style
      self.dialog.endPointSelection()

  def updateDEMSize(self, v=None):
    # calculate DEM size and grid spacing
    canvas = self.dialog.iface.mapCanvas()
    canvasSize = canvas.mapSettings().outputSize()
    resolutionLevel = self.horizontalSlider_DEMSize.value()
    roughening = self.spinBox_Roughening.value() if self.checkBox_Surroundings.isChecked() else 0
    demSize = calculateDEMSize(canvasSize, resolutionLevel, roughening)

    mupp = canvas.mapUnitsPerPixel()
    xres = (mupp * canvasSize.width()) / (demSize.width() - 1)
    yres = (mupp * canvasSize.height()) / (demSize.height() - 1)

    # update labels
    self.label_Resolution.setText("{0} x {1}".format(demSize.width(), demSize.height()))   #TODO: label_GridSize
    self.lineEdit_HRes.setText(str(xres))
    self.lineEdit_VRes.setText(str(yres))

  def properties(self):
    p = PropertyPage.properties(self)
    item = self.dialog.currentItem
    if item is not None:
      p["visible"] = item.data(0, Qt.CheckStateRole) == Qt.Checked
    if self.layerImageIds:
      p["layerImageIds"] = self.layerImageIds
    return p

  def setProperties(self, properties):
    PropertyPage.setProperties(self, properties)
    self.layerImageIds = properties.get("layerImageIds", [])

  def updateQuads(self, v=None):
    isSimpleMode = self.radioButton_Simple.isChecked()
    if isSimpleMode:
      self.dialog.clearRubberBands()
      return

    canvas = self.dialog.iface.mapCanvas()
    mapSettings = canvas.mapSettings()
    baseExtent = RotatedRect.fromMapSettings(mapSettings)
    p = {"lineEdit_centerX": self.lineEdit_centerX.text(),
         "lineEdit_centerY": self.lineEdit_centerY.text(),
         "lineEdit_rectWidth": self.lineEdit_rectWidth.text(),
         "lineEdit_rectHeight": self.lineEdit_rectHeight.text(),
         "spinBox_Height": self.spinBox_Height.value()}

    quadtree = createQuadTree(baseExtent, p)
    if quadtree:
      self.dialog.createRubberBands(baseExtent, quadtree)
      self.dialog.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
    else:
      self.dialog.clearRubberBands()

  def rectangleSelected(self):
    self.radioButton_Advanced.setChecked(True)
    rect = self.dialog.mapTool.rectangle()    # RotatedRect object
    toRect = rect.width() and rect.height()
    self.switchFocusMode(toRect)

    center = rect.center()
    self.lineEdit_centerX.setText(str(center.x()))
    self.lineEdit_centerY.setText(str(center.y()))
    self.lineEdit_rectWidth.setText(str(rect.width()))
    self.lineEdit_rectHeight.setText(str(rect.height()))

    # update quad rubber bands
    self.updateQuads()

  def dispTypeChanged(self, checked=True):
    if checked:
      if self.radioButton_MapCanvas.isChecked():
        t = 0
      elif self.radioButton_LayerImage.isChecked():
        t = 1
      elif self.radioButton_ImageFile.isChecked():
        t = 2
      else:   # self.radioButton_SolidColor.isChecked():
        t = 3

      self.setWidgetsEnabled([self.label_TextureSize, self.comboBox_TextureSize], t in [0, 1])

      self.checkBox_TransparentBackground.setEnabled(t in [0, 1, 2])
      if t in [0, 1]:
        self.checkBox_TransparentBackground.setText("Transparent background")
      elif t == 2:
        self.checkBox_TransparentBackground.setText("Enable transparency")

  def samplingModeChanged(self, checked):
    isSimpleMode = self.radioButton_Simple.isChecked()
    isAdvancedMode = not isSimpleMode
    surroundings = self.checkBox_Surroundings.isChecked()
    is_simple_wo_surroundings = isSimpleMode and not surroundings

    self.setLayoutsEnabled([self.verticalLayout_Simple], isSimpleMode)
    self.setLayoutsEnabled([self.gridLayout_Surroundings], isSimpleMode and surroundings)
    self.setWidgetsEnabled([self.radioButton_ImageFile, self.groupBox_Clip], is_simple_wo_surroundings)

    if self.isPrimary:
      self.setLayoutsVisible([self.horizontalLayout_Advanced1, self.horizontalLayout_Advanced3], isAdvancedMode)
      self.setWidgetsVisible([self.label_Focus], isAdvancedMode)

      if isSimpleMode:
        self.setLayoutVisible(self.horizontalLayout_Advanced4, False)
      else:
        try:
          isPoint = (float(self.lineEdit_rectWidth.text()) == 0 and float(self.lineEdit_rectHeight.text()) == 0)
        except ValueError:
          isPoint = True
        self.switchFocusMode(not isPoint)

    if isAdvancedMode and self.radioButton_ImageFile.isChecked():
      self.radioButton_MapCanvas.setChecked(True)

    # update quad rubber bands
    self.updateQuads()

  def switchFocusMode(self, toRect):
    self.setLayoutVisible(self.horizontalLayout_Advanced4, toRect)

    selection = "area" if toRect else "point"
    action = "Stroke a rectangle" if toRect else "Click"
    self.label_Focus.setText("Focus {0} ({1} on map canvas to set values)".format(selection, action))


class VectorPropertyPage(PropertyPage, Ui_VectorPropertiesWidget):

  STYLE_MAX_COUNT = 6

  def __init__(self, dialog, parent=None):
    PropertyPage.__init__(self, PAGE_VECTOR, dialog, parent)
    Ui_VectorPropertiesWidget.setupUi(self, self)

    self.layer = None

    # initialize vector style widgets
    self.labelHeightWidget = StyleWidget(StyleWidget.LABEL_HEIGHT)
    self.labelHeightWidget.setObjectName("labelHeightWidget")
    self.labelHeightWidget.setEnabled(False)
    self.verticalLayout_Label.addWidget(self.labelHeightWidget)

    self.styleWidgetCount = 0
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

    widgets = [self.comboBox_ObjectType]
    widgets += [self.radioButton_Absolute, self.radioButton_Relative, self.comboBox_zDEMLayer]
    widgets += [self.radioButton_zValue, self.radioButton_mValue, self.radioButton_FieldValue, self.fieldExpressionWidget_zCoordinate]
    widgets += self.styleWidgets
    widgets += [self.radioButton_AllFeatures, self.radioButton_IntersectingFeatures, self.checkBox_Clip]
    widgets += [self.checkBox_ExportAttrs, self.comboBox_Label, self.labelHeightWidget]
    self.registerPropertyWidgets(widgets)

    self.comboBox_ObjectType.currentIndexChanged.connect(self.setupStyleWidgets)
    #self.heightWidget.comboBox.currentIndexChanged.connect(self.altitudeModeChanged) #TODO
    self.checkBox_ExportAttrs.toggled.connect(self.exportAttrsToggled)

  def setup(self, properties=None, layer=None):   # TODO: layer is required. layer, properties=None
    self.layer = layer

    if self.dialog.currentItem:
      self.setEnabled(self.dialog.currentItem.data(0, Qt.CheckStateRole) == Qt.Checked)
    else:
      self.setEnabled(True)

    for i in range(self.STYLE_MAX_COUNT):
      self.styleWidgets[i].hide()

    obj_types = objectTypeManager().objectTypeNames(layer.geometryType())

    # set up object type combo box
    self.comboBox_ObjectType.blockSignals(True)
    self.comboBox_ObjectType.clear()
    for index, obj_type in enumerate(obj_types):
      self.comboBox_ObjectType.addItem(obj_type, index)
    if properties:
      # restore object type selection
      self.comboBox_ObjectType.setCurrentIndex(properties.get("comboBox_ObjectType", 0))
    self.comboBox_ObjectType.blockSignals(False)

    # populate DEM layer items (relative to DEM)
    for lyr in tools.getDEMLayersInProject():
      self.comboBox_zDEMLayer.addItem(lyr.name(), lyr.id())

    # get MapTo3D object to calculate default values
    mapTo3d = self.dialog.mapTo3d()

    # set up z/m button
    wkbType = layer.wkbType()
    hasZ = wkbType in [QgsWkbTypes.Point25D, QgsWkbTypes.LineString25D,
                       QgsWkbTypes.MultiPoint25D, QgsWkbTypes.MultiLineString25D]  #TODO: ,MultiPolygon25D
    hasZ = hasZ or (wkbType // 1000 in [1, 3])
    hasM = (wkbType // 1000 in [2, 3])
    self.radioButton_zValue.setEnabled(hasZ)
    self.radioButton_mValue.setEnabled(hasM)

    if hasZ:
      self.radioButton_zValue.setChecked(True)
    else:
      self.radioButton_FieldValue.setChecked(True)

    # set up field expression widget (z coordinate)
    self.fieldExpressionWidget_zCoordinate.setFilters(QgsFieldProxyModel.Numeric)
    self.fieldExpressionWidget_zCoordinate.setLayer(layer)
    self.fieldExpressionWidget_zCoordinate.setExpression("0")

    # set up label height widget
    if layer.geometryType() != QgsWkbTypes.LineGeometry:
      defaultLabelHeight = 5
      self.labelHeightWidget.setup(options={"layer": layer, "defaultValue": defaultLabelHeight / mapTo3d.multiplierZ})
    else:
      self.labelHeightWidget.hide()

    # point layer has no geometry clip option
    self.checkBox_Clip.setVisible(layer.geometryType() != QgsWkbTypes.PointGeometry)

    # set up style widgets for selected object type
    self.setupStyleWidgets()

    # set up label combo box
    hasPoint = (layer.geometryType() in (QgsWkbTypes.PointGeometry, QgsWkbTypes.PolygonGeometry))
    self.setLayoutVisible(self.formLayout_Label, hasPoint)
    self.comboBox_Label.clear()
    if hasPoint:
      self.comboBox_Label.addItem("(No label)")
      fields = self.layer.pendingFields()
      for i in range(fields.count()):
        self.comboBox_Label.addItem(fields[i].name(), i)

    # restore other properties for the layer
    self.setProperties(properties or {})

  def setupStyleWidgets(self, index=None):
    index = self.comboBox_ObjectType.currentIndex()

    # notice 3D model is experimental
    is_experimental = self.comboBox_ObjectType.currentText() in ["JSON model", "COLLADA model"]
    self.label_ObjectTypeMessage.setVisible(is_experimental)

    # get MapTo3D object to calculate default values
    mapTo3d = self.dialog.mapTo3d()

    # setup widgets
    objectTypeManager().setupWidgets(self, mapTo3d, self.layer, self.layer.geometryType(), index)

    # update enabled property of feature group box
    self.altitudeModeChanged()

  def itemChanged(self, item):
    self.setEnabled(item.data(0, Qt.CheckStateRole) == Qt.Checked)

  def altitudeModeChanged(self, index=None):
    geom_type = self.layer.geometryType()
    type_index = self.comboBox_ObjectType.currentIndex()
    only_clipped = False

    if (geom_type == QgsWkbTypes.LineGeometry and type_index == 4) or (geom_type == QgsWkbTypes.PolygonGeometry and type_index == 1):    # Profile or Overlay
      if self.heightWidget.func.isCurrentItemRelativeHeight():
        only_clipped = True
        self.radioButton_IntersectingFeatures.setChecked(True)
        self.checkBox_Clip.setChecked(True)

    self.groupBox_Features.setEnabled(not only_clipped)

  def exportAttrsToggled(self, checked):
    self.setLayoutEnabled(self.formLayout_Label, checked)
    self.labelHeightWidget.setEnabled(checked)

  def properties(self):
    p = PropertyPage.properties(self)
    item = self.dialog.currentItem
    if item is not None:
      p["visible"] = item.data(0, Qt.CheckStateRole) == Qt.Checked
    return p

  def initStyleWidgets(self, color=True, opacity=True):
    self.styleWidgetCount = 0

    if color:
      self.addStyleWidget(StyleWidget.COLOR)

    if opacity:
      self.addStyleWidget(StyleWidget.OPACITY)

    for i in range(self.styleWidgetCount, self.STYLE_MAX_COUNT):
      self.styleWidgets[i].hide()

  def addStyleWidget(self, funcType=None, options=None):
    self.styleWidgets[self.styleWidgetCount].setup(funcType, options)
    self.styleWidgetCount += 1
