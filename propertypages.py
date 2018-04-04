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

from PyQt5.QtCore import Qt, QDir, QPoint
from PyQt5.QtWidgets import QCheckBox, QColorDialog, QComboBox, QFileDialog, QLineEdit, QRadioButton, QSlider, QSpinBox, QToolTip, QWidget
from PyQt5.QtGui import QColor
from qgis.core import QgsFieldProxyModel, QgsMapLayer, QgsWkbTypes
from qgis.gui import QgsFieldExpressionWidget

from .ui.worldproperties import Ui_WorldPropertiesWidget
from .ui.demproperties import Ui_DEMPropertiesWidget
from .ui.vectorproperties import Ui_VectorPropertiesWidget

from .conf import def_vals
from .qgis2threejscore import calculateDEMSize
from .qgis2threejstools import getLayersInProject, logMessage
from .stylewidget import StyleWidget, LabelHeightWidgetFunc
from . import qgis2threejstools as tools
from .vectorobject import objectTypeRegistry

PAGE_NONE = 0
PAGE_WORLD = 1
#PAGE_CONTROLS = 2
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

    canvas = self.dialog.iface.mapCanvas()
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


class DEMPropertyPage(PropertyPage, Ui_DEMPropertiesWidget):

  def __init__(self, dialog, parent=None):
    PropertyPage.__init__(self, PAGE_DEM, dialog, parent)
    Ui_DEMPropertiesWidget.setupUi(self, self)

    # set read only to line edits of spin boxes
    self.spinBox_Size.findChild(QLineEdit).setReadOnly(True)
    self.spinBox_Roughening.findChild(QLineEdit).setReadOnly(True)

    self.layer = None
    self.layerImageIds = []

    dispTypeButtons = [self.radioButton_MapCanvas, self.radioButton_LayerImage, self.radioButton_ImageFile, self.radioButton_SolidColor]
    widgets = [self.spinBox_Opacity, self.horizontalSlider_DEMSize]
    widgets += [self.checkBox_Surroundings, self.spinBox_Size, self.spinBox_Roughening]
    widgets += dispTypeButtons
    widgets += [self.checkBox_TransparentBackground, self.lineEdit_ImageFile, self.lineEdit_Color, self.comboBox_TextureSize, self.checkBox_Shading]
    widgets += [self.checkBox_Clip, self.comboBox_ClipLayer]
    widgets += [self.checkBox_Sides, self.checkBox_Frame]
    self.registerPropertyWidgets(widgets)

    self.initLayerComboBox()
    self.initTextureSizeComboBox()

    self.horizontalSlider_DEMSize.valueChanged.connect(self.resolutionSliderChanged)
    self.checkBox_Surroundings.toggled.connect(self.surroundingsToggled)
    self.spinBox_Roughening.valueChanged.connect(self.rougheningChanged)
    for radioButton in dispTypeButtons:
      radioButton.toggled.connect(self.dispTypeChanged)
    self.toolButton_SelectLayer.clicked.connect(self.selectLayerClicked)
    self.toolButton_ImageFile.clicked.connect(self.browseClicked)
    self.toolButton_Color.clicked.connect(self.colorButtonClicked)

  def setup(self, layer=None):
    self.layer = layer
    properties = layer.properties

    # show/hide resampling slider
    self.setLayoutVisible(self.horizontalLayout_Resampling, layer.layerId != "FLAT")

    # use default properties if properties is not set
    if not properties:
      properties = self.properties()
      properties["comboBox_TextureSize"] = 100
      properties["checkBox_Sides"] = True

    # restore properties of the layer
    self.setProperties(properties)

    self.updateLayerImageLabel()

    # set enablement and visibility of widgets
    self.surroundingsToggled(self.checkBox_Surroundings.isChecked())
    self.dispTypeChanged()

  def initLayerComboBox(self):
    # list of polygon layers
    self.comboBox_ClipLayer.clear()
    for layer in getLayersInProject():
      if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
        self.comboBox_ClipLayer.addItem(layer.name(), layer.id())

  def initTextureSizeComboBox(self):
    canvas = self.dialog.iface.mapCanvas()
    outsize = canvas.mapSettings().outputSize()

    self.comboBox_TextureSize.clear()
    for i in [4, 2, 1]:
      percent = i * 100
      text = "{0} %  ({1} x {2} px)".format(percent, outsize.width() * i, outsize.height() * i)
      self.comboBox_TextureSize.addItem(text, percent)

  def resolutionSliderChanged(self, v):
    canvas = self.dialog.iface.mapCanvas()
    canvasSize = canvas.mapSettings().outputSize()
    resolutionLevel = self.horizontalSlider_DEMSize.value()
    roughening = self.spinBox_Roughening.value() if self.checkBox_Surroundings.isChecked() else 0
    demSize = calculateDEMSize(canvasSize, resolutionLevel, roughening)

    mupp = canvas.mapUnitsPerPixel()
    xres = (mupp * canvasSize.width()) / (demSize.width() - 1)
    yres = (mupp * canvasSize.height()) / (demSize.height() - 1)

    tip = """Level {0}
Grid Size: {1} x {2}
Grid Spacing: {3:.5f} x {4:.5f})""".format(resolutionLevel,
                                           demSize.width(), demSize.height(),
                                           xres, yres)
    QToolTip.showText(self.horizontalSlider_DEMSize.mapToGlobal(QPoint(0, 0)), tip, self.horizontalSlider_DEMSize)

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
    self.setLayoutEnabled(self.gridLayout_Surroundings, checked)
    self.setLayoutEnabled(self.verticalLayout_Clip, not checked)
    self.setWidgetsEnabled([self.radioButton_ImageFile], not checked)

    if checked and self.radioButton_ImageFile.isChecked():
      self.radioButton_MapCanvas.setChecked(True)

  def rougheningChanged(self, v):
    # possible value is a power of 2
    self.spinBox_Roughening.setSingleStep(v)
    self.spinBox_Roughening.setMinimum(max(v // 2, 1))

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
    widgets += self.buttonGroup_altitude.buttons() + [self.fieldExpressionWidget_altitude, self.comboBox_altitudeMode]
    widgets += self.styleWidgets
    widgets += [self.radioButton_AllFeatures, self.radioButton_IntersectingFeatures, self.checkBox_Clip]
    widgets += [self.checkBox_ExportAttrs, self.comboBox_Label, self.labelHeightWidget]
    self.registerPropertyWidgets(widgets)

    self.comboBox_ObjectType.currentIndexChanged.connect(self.setupStyleWidgets)
    self.comboBox_altitudeMode.currentIndexChanged.connect(self.altitudeModeChanged)
    for btn in self.buttonGroup_altitude.buttons():
      btn.toggled.connect(self.zValueRadioButtonToggled)
    self.checkBox_ExportAttrs.toggled.connect(self.exportAttrsToggled)

  def setup(self, layer):
    self.layer = layer
    mapLayer = layer.mapLayer
    properties = layer.properties

    if self.dialog.currentItem:
      self.setEnabled(self.dialog.currentItem.data(0, Qt.CheckStateRole) == Qt.Checked)
    else:
      self.setEnabled(True)

    for i in range(self.STYLE_MAX_COUNT):
      self.styleWidgets[i].hide()

    # set up object type combo box
    self.comboBox_ObjectType.blockSignals(True)
    self.comboBox_ObjectType.clear()
    for obj_type in objectTypeRegistry().objectTypes(mapLayer.geometryType()):
      self.comboBox_ObjectType.addItem(obj_type.displayName(), obj_type.name)
    if properties:
      # restore object type selection
      idx = self.comboBox_ObjectType.findData(properties.get("comboBox_ObjectType"))
      if idx != -1:
        self.comboBox_ObjectType.setCurrentIndex(idx)
    self.comboBox_ObjectType.blockSignals(False)

    # set up altitude mode combo box
    self.comboBox_altitudeMode.blockSignals(True)
    self.comboBox_altitudeMode.clear()
    self.comboBox_altitudeMode.addItem("Absolute")
    for lyr in tools.getDEMLayersInProject():
      self.comboBox_altitudeMode.addItem('Relative to "{0}" layer'.format(lyr.name()), lyr.id())
    self.comboBox_altitudeMode.blockSignals(False)

    # set up z/m button
    wkbType = mapLayer.wkbType()
    hasZ = wkbType in [QgsWkbTypes.Point25D, QgsWkbTypes.LineString25D,
                       QgsWkbTypes.MultiPoint25D, QgsWkbTypes.MultiLineString25D]  #TODO: [Polygon z/m support] ,MultiPolygon25D
    hasZ = hasZ or (wkbType // 1000 in [1, 3])
    hasM = (wkbType // 1000 in [2, 3])
    self.radioButton_zValue.setEnabled(hasZ)
    self.radioButton_mValue.setEnabled(hasM)

    if hasZ:
      self.radioButton_zValue.setChecked(True)
    else:
      self.radioButton_Expression.setChecked(True)

    # set up field expression widget
    self.fieldExpressionWidget_altitude.setFilters(QgsFieldProxyModel.Numeric)
    self.fieldExpressionWidget_altitude.setLayer(mapLayer)
    self.fieldExpressionWidget_altitude.setExpression("0")

    # set up label height widget
    if mapLayer.geometryType() != QgsWkbTypes.LineGeometry:
      defaultLabelHeight = 5
      mapTo3d = self.dialog.mapTo3d()
      self.labelHeightWidget.setup(options={"layer": mapLayer, "defaultValue": defaultLabelHeight / mapTo3d.multiplierZ})
      if mapLayer.geometryType() == QgsWkbTypes.PointGeometry:
        self.setupLabelHeightWidget([(LabelHeightWidgetFunc.RELATIVE, "Height from point")])
    else:
      self.labelHeightWidget.hide()

    # point layer has no geometry clip option
    self.checkBox_Clip.setVisible(mapLayer.geometryType() != QgsWkbTypes.PointGeometry)

    # set up style widgets for selected object type
    self.setupStyleWidgets()

    # set up label combo box
    hasPoint = (mapLayer.geometryType() in (QgsWkbTypes.PointGeometry, QgsWkbTypes.PolygonGeometry))
    self.setLayoutVisible(self.formLayout_Label, hasPoint)
    self.comboBox_Label.clear()
    if hasPoint:
      self.comboBox_Label.addItem("(No label)")
      fields = mapLayer.fields()
      for i in range(fields.count()):
        self.comboBox_Label.addItem(fields[i].name(), i)

    # restore other properties for the layer
    self.setProperties(properties or {})

  def setupStyleWidgets(self, index=None):
    # setup widgets
    obj_type = objectTypeRegistry().objectType(self.layer.mapLayer.geometryType(),
                                               self.comboBox_ObjectType.currentData())
    obj_type.setupWidgets(self,
                          self.dialog.mapTo3d(),     # to calculate default values
                          self.layer.mapLayer)

  def itemChanged(self, item):
    self.setEnabled(item.data(0, Qt.CheckStateRole) == Qt.Checked)

  def altitudeModeChanged(self, index):
    name = self.comboBox_ObjectType.currentData()
    only_clipped = False

    if name in ["Profile", "Overlay"] and index:
      only_clipped = True
      self.radioButton_IntersectingFeatures.setChecked(True)
      self.checkBox_Clip.setChecked(True)

    self.groupBox_Features.setEnabled(not only_clipped)

  def zValueRadioButtonToggled(self, toggled=None):
    if toggled != False:
      self.label_zExpression.setText("" if self.radioButton_Expression.isChecked() else "Addend")

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
      self.addStyleWidget(StyleWidget.COLOR, {"layer": self.layer.mapLayer})

    if opacity:
      self.addStyleWidget(StyleWidget.OPACITY, {"layer": self.layer.mapLayer})

    for i in range(self.styleWidgetCount, self.STYLE_MAX_COUNT):
      self.styleWidgets[i].hide()

  def addStyleWidget(self, funcType=None, options=None):
    self.styleWidgets[self.styleWidgetCount].setup(funcType, options)
    self.styleWidgetCount += 1

  def setupLabelHeightWidget(self, item_list):
    self.labelHeightWidget.setup(options={"items": item_list})
