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
import json
import re

from PyQt5.QtCore import Qt, QDir, QPoint, QUrl
from PyQt5.QtWidgets import QAction, QCheckBox, QComboBox, QFileDialog, QLineEdit, QMenu, QRadioButton, QSlider, QSpinBox, QToolTip, QWidget
from PyQt5.QtGui import QColor, QCursor
from qgis.core import Qgis, QgsCoordinateTransform, QgsFieldProxyModel, QgsMapLayer, QgsProject, QgsWkbTypes
from qgis.gui import QgsColorButton, QgsFieldExpressionWidget

try:
    from processing.gui.RectangleMapTool import RectangleMapTool
    HAVE_PROCESSING = True
except:
    HAVE_PROCESSING = False

from .ui.sceneproperties import Ui_ScenePropertiesWidget
from .ui.demproperties import Ui_DEMPropertiesWidget
from .ui.vectorproperties import Ui_VectorPropertiesWidget
from .ui.pcproperties import Ui_PCPropertiesWidget

from .conf import DEF_SETS
from .datamanager import MaterialManager
from .mapextent import MapExtent
from .pluginmanager import pluginManager
from .qgis2threejscore import calculateGridSegments
from .qgis2threejstools import getLayersInProject, logMessage
from .stylewidget import StyleWidget
from . import qgis2threejstools as tools
from .vectorobject import ObjectType

PAGE_NONE = 0
PAGE_SCENE = 1
# PAGE_CONTROLS = 2
PAGE_DEM = 3
PAGE_VECTOR = 4
PAGE_POINTCLOUD = 5


def is_number(val):
    try:
        float(val)
        return True
    except ValueError:
        return False


class PropertyPage(QWidget):

    def __init__(self, pageType, parent=None):
        QWidget.__init__(self, parent)
        self.pageType = pageType
        self.dialog = parent
        self.propertyWidgets = []

    def itemChanged(self, item):
        pass

    def setLayoutVisible(self, layout, visible):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            w = item.widget()
            if w:
                w.setVisible(visible)
                continue
            lyt = item.layout()
            if lyt:
                self.setLayoutVisible(lyt, visible)

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
            if w:
                w.setEnabled(enabled)
                continue
            lyt = item.layout()
            if lyt:
                self.setLayoutEnabled(lyt, enabled)

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
                v = w.currentData()
                if v is None and w.isEditable():
                    v = w.currentText()
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
            elif isinstance(w, QgsColorButton):
                v = w.color().name().replace("#", "0x")
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
                    elif w.isEditable():
                        w.setEditText(str(v))
            elif isinstance(w, (QRadioButton, QCheckBox)):  # subclass of QAbstractButton
                w.setChecked(v)
            elif isinstance(w, (QSlider, QSpinBox)):
                w.setValue(v)
            elif isinstance(w, QLineEdit):
                w.setText(v)
                w.setCursorPosition(0)
            elif isinstance(w, StyleWidget):
                if len(v):
                    w.setValues(v)
            elif isinstance(w, QgsFieldExpressionWidget):
                w.setExpression(v)
            elif isinstance(w, QgsColorButton):
                w.setColor(QColor(v.replace("0x", "#")))
            else:
                logMessage("[propertypages.py] Cannot restore %s property" % n)


class ScenePropertyPage(PropertyPage, Ui_ScenePropertiesWidget):

    def __init__(self, parent=None):
        PropertyPage.__init__(self, PAGE_SCENE, parent)
        Ui_ScenePropertiesWidget.setupUi(self, self)

        widgets = [self.radioButton_FixedExtent, self.lineEdit_CenterX, self.lineEdit_CenterY,
                   self.lineEdit_Width, self.lineEdit_Height, self.lineEdit_Rotation, self.checkBox_FixAspectRatio,
                   self.lineEdit_BaseSize, self.lineEdit_zFactor, self.lineEdit_zShift, self.checkBox_autoZShift,
                   self.comboBox_MaterialType, self.checkBox_Outline,
                   self.radioButton_Color, self.colorButton_Color,
                   self.radioButton_WGS84]
        self.registerPropertyWidgets(widgets)

        # material type
        self.comboBox_MaterialType.addItem("Lambert Material", MaterialManager.MESH_LAMBERT)
        self.comboBox_MaterialType.addItem("Phong Material", MaterialManager.MESH_PHONG)
        self.comboBox_MaterialType.addItem("Toon Material", MaterialManager.MESH_TOON)

        self.radioButton_FixedExtent.toggled.connect(self.fixedExtentToggled)
        self.lineEdit_Width.editingFinished.connect(self.widthEditingFinished)
        self.pushButton_SelectExtent.clicked.connect(self.showSelectExtentMenu)
        self.checkBox_FixAspectRatio.toggled.connect(self.fixAspectRatioToggled)

    def setup(self, properties, mapSettings, canvas):

        self.mapSettings = mapSettings

        if HAVE_PROCESSING:
            self.initMapTool(canvas)

        # restore properties
        if properties:
            self.setProperties(properties)
        else:
            self.radioButton_UseCanvasExtent.setChecked(True)
            self.lineEdit_BaseSize.setText(str(DEF_SETS.BASE_SIZE))
            self.lineEdit_zFactor.setText(str(DEF_SETS.Z_EXAGGERATION))
            self.lineEdit_zShift.setText(str(DEF_SETS.Z_SHIFT))
            self.checkBox_autoZShift.setChecked(DEF_SETS.AUTO_Z_SHIFT)

        # map extent (2D)
        if self.radioButton_UseCanvasExtent.isChecked():
            self.fixedExtentToggled(False)

        # Supported projections
        # https://github.com/proj4js/proj4js
        projs = ["longlat", "merc"]
        projs += ["aea", "aeqd", "cass", "cea", "eqc", "eqdc", "etmerc", "geocent", "gnom", "krovak", "laea", "lcc", "mill", "moll",
                  "nzmg", "omerc", "ortho", "poly", "qsc", "robin", "sinu", "somerc", "stere", "sterea", "tmerc", "tpers", "utm", "vandg"]

        crs = QgsProject.instance().crs()
        proj = crs.toProj4() if Qgis.QGIS_VERSION_INT < 31003 else crs.toProj()
        m = re.search(r"\+proj=(\w+)", proj)
        proj_supported = bool(m and m.group(1) in projs)

        if not proj_supported:
            self.radioButton_ProjectCRS.setChecked(True)
        self.radioButton_WGS84.setEnabled(proj_supported)

    def initMapTool(self, canvas):
        try:
            self.canvas = canvas
            self.prevMapTool = canvas.mapTool()
            self.mapTool = RectangleMapTool(canvas)
            self.mapTool.rectangleCreated.connect(self.updateExtent)
            return True
        except:
            HAVE_PROCESSING = False
            return False

    def properties(self):
        p = PropertyPage.properties(self)
        # check validity
        if not is_number(self.lineEdit_BaseSize.text()):
            p["lineEdit_BaseSize"] = str(DEF_SETS.BASE_SIZE)
        if not is_number(self.lineEdit_zFactor.text()):
            p["lineEdit_zFactor"] = str(DEF_SETS.Z_EXAGGERATION)
        if not is_number(self.lineEdit_zShift.text()):
            p["lineEdit_zShift"] = str(DEF_SETS.Z_SHIFT)
        return p

    def setExtent(self, extent=None):
        be = extent or MapExtent.fromMapSettings(self.mapSettings, self.checkBox_FixAspectRatio.isChecked())
        self.lineEdit_CenterX.setText(str(be.center().x()))
        self.lineEdit_CenterY.setText(str(be.center().y()))
        self.lineEdit_Width.setText(str(be.width()))
        self.lineEdit_Height.setText(str(be.height()))
        self.lineEdit_Rotation.setText(str(be.rotation()))

        for i in range(self.gridLayout_Extent.count()):
            w = self.gridLayout_Extent.itemAt(i).widget()
            if isinstance(w, QLineEdit):
                w.setCursorPosition(0)

    def fixedExtentToggled(self, checked):
        self.setLayoutEnabled(self.gridLayout_Extent, checked)

        if checked:
            if self.checkBox_FixAspectRatio.isChecked():
                self.fixAspectRatioToggled(True)
        else:
            self.setExtent()

    def fixAspectRatioToggled(self, checked):
        if self.radioButton_FixedExtent.isChecked():
            self.lineEdit_Height.setEnabled(not checked)
            if checked:
                try:
                    w, h = (float(self.lineEdit_Width.text()), float(self.lineEdit_Height.text()))
                    if w > h:
                        self.lineEdit_Height.setText(self.lineEdit_Width.text())
                    else:
                        self.lineEdit_Width.setText(self.lineEdit_Height.text())

                    self.lineEdit_Width.setCursorPosition(0)
                    self.lineEdit_Height.setCursorPosition(0)
                except ValueError:
                    pass
        else:
            self.setExtent()

    def widthEditingFinished(self):
        if self.checkBox_FixAspectRatio.isChecked():
            self.lineEdit_Height.setText(self.lineEdit_Width.text())
            self.lineEdit_Height.setCursorPosition(0)

    def showSelectExtentMenu(self):
        popup = QMenu()

        if HAVE_PROCESSING:
            selectOnCanvasAction = QAction("Select Extent on Canvas", self.pushButton_SelectExtent)
            selectOnCanvasAction.triggered.connect(self.selectExtentOnCanvas)
            popup.addAction(selectOnCanvasAction)
            popup.addSeparator()

        useLayerExtentAction = QAction("Use Layer Extent...", self.pushButton_SelectExtent)
        useLayerExtentAction.triggered.connect(self.useLayerExtent)
        popup.addAction(useLayerExtentAction)

        popup.exec_(QCursor.pos())

    def selectExtentOnCanvas(self):
        self.canvas.setMapTool(self.mapTool)

        self.dialog.wnd.showMinimized()

    def updateExtent(self):
        self.checkBox_FixAspectRatio.setChecked(False)

        r = self.mapTool.rectangle()
        extent = MapExtent(r.center(), r.width(), r.height(), self.canvas.mapSettings().rotation()) # get current map settings
        self.setExtent(extent)

        self.mapTool.reset()
        self.canvas.setMapTool(self.prevMapTool)

        wnd = self.dialog.wnd
        wnd.showNormal()
        wnd.activateWindow()

    def useLayerExtent(self):
        from .layerselectdialog import SingleLayerSelectDialog
        dlg = SingleLayerSelectDialog(self, "Use extent from")
        dlg.setWindowTitle("Select Extent")
        if dlg.exec_():
            layer = dlg.selectedLayer()

            transform = QgsCoordinateTransform(layer.crs(), self.mapSettings.destinationCrs(), QgsProject.instance())
            r = transform.transformBoundingBox(layer.extent())

            self.checkBox_FixAspectRatio.setChecked(False)

            extent = MapExtent(r.center(), r.width(), r.height())
            self.setExtent(extent)


class DEMPropertyPage(PropertyPage, Ui_DEMPropertiesWidget):

    def __init__(self, parent=None):
        PropertyPage.__init__(self, PAGE_DEM, parent)
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
        widgets += [self.checkBox_TransparentBackground, self.lineEdit_ImageFile, self.colorButton_Color, self.comboBox_TextureSize, self.checkBox_Shading]
        widgets += [self.checkBox_Clip, self.comboBox_ClipLayer]
        widgets += [self.checkBox_Sides, self.toolButton_SideColor,
                    self.checkBox_Frame, self.toolButton_EdgeColor,
                    self.checkBox_Wireframe, self.toolButton_WireframeColor, self.checkBox_Visible, self.checkBox_Clickable]
        self.registerPropertyWidgets(widgets)

        self.initLayerComboBox()

        self.comboBox_TextureSize.addItem("512")
        self.comboBox_TextureSize.addItem("1024")
        self.comboBox_TextureSize.addItem("2048")
        self.comboBox_TextureSize.insertSeparator(3)
        self.comboBox_TextureSize.addItem("Map Canvas Width")

        self.horizontalSlider_DEMSize.valueChanged.connect(self.resolutionSliderChanged)
        self.checkBox_Surroundings.toggled.connect(self.surroundingsToggled)
        self.checkBox_Clip.toggled.connect(self.clipToggled)
        self.spinBox_Roughening.valueChanged.connect(self.rougheningChanged)
        for radioButton in dispTypeButtons:
            radioButton.toggled.connect(self.dispTypeChanged)
        self.toolButton_SelectLayer.clicked.connect(self.selectLayerClicked)
        self.toolButton_ImageFile.clicked.connect(self.browseClicked)

    def setup(self, layer, extent, mapSettings):
        self.layer = layer
        properties = layer.properties
        self.extent = extent
        self.mapSettings = mapSettings

        # show/hide resampling slider
        self.setLayoutVisible(self.horizontalLayout_Resampling, layer.layerId != "FLAT")

        if properties:
            if "toolButton_EdgeColor" not in properties:        # this means "if loaded properties were saved in plugin version < 2.6"
                properties["comboBox_TextureSize"] = "Map Canvas Width"
        else:
            # use default properties if properties is not set
            properties = self.properties()
            properties["toolButton_SideColor"] = DEF_SETS.SIDE_COLOR
            properties["comboBox_TextureSize"] = 1024

        properties["toolButton_EdgeColor"] = properties.get("toolButton_EdgeColor", DEF_SETS.EDGE_COLOR)                   # added in 2.6
        properties["toolButton_WireframeColor"] = properties.get("toolButton_WireframeColor", DEF_SETS.WIREFRAME_COLOR)    # added in 2.6

        # restore properties of the layer
        self.setProperties(properties)

        self.updateLayerImageLabel()

        # set enablement and visibility of widgets
        self.surroundingsToggled(self.checkBox_Surroundings.isChecked())
        self.comboBox_ClipLayer.setVisible(self.checkBox_Clip.isChecked())
        self.dispTypeChanged()

    def initLayerComboBox(self):
        # list of polygon layers
        self.comboBox_ClipLayer.blockSignals(True)
        self.comboBox_ClipLayer.clear()
        for layer in getLayersInProject():
            if layer.type() == QgsMapLayer.VectorLayer and layer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.comboBox_ClipLayer.addItem(layer.name(), layer.id())

        self.comboBox_ClipLayer.blockSignals(False)

    def resolutionSliderChanged(self, v):
        resolutionLevel = self.horizontalSlider_DEMSize.value()
        roughness = self.spinBox_Roughening.value() if self.checkBox_Surroundings.isChecked() else 0
        gridSegments = calculateGridSegments(self.extent, resolutionLevel, roughness)

        tip = """Level: {0}
Grid Segments: {1} x {2}
Grid Spacing: {3:.5f} x {4:.5f}{5}""".format(resolutionLevel,
                                             gridSegments.width(), gridSegments.height(),
                                             self.extent.width() / gridSegments.width(),
                                             self.extent.height() / gridSegments.height(),
                                             "" if self.extent.width() == self.extent.height() else " (Approx.)")
        QToolTip.showText(self.horizontalSlider_DEMSize.mapToGlobal(QPoint(0, 0)), tip, self.horizontalSlider_DEMSize)

    def selectLayerClicked(self):
        from .layerselectdialog import LayerSelectDialog
        dialog = LayerSelectDialog(self)
        dialog.initTree(self.layerImageIds)
        dialog.setMapSettings(self.mapSettings)
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

    def surroundingsToggled(self, checked):
        self.setLayoutVisible(self.gridLayout_Surroundings, checked)
        self.setLayoutEnabled(self.verticalLayout_Clip, not checked)
        self.setWidgetsEnabled([self.radioButton_ImageFile], not checked)

        if checked:
            self.checkBox_Clip.setChecked(False)

        if checked and self.radioButton_ImageFile.isChecked():
            self.radioButton_MapCanvas.setChecked(True)

    def clipToggled(self, checked):
        if checked:
            self.checkBox_Frame.setChecked(False)
            self.checkBox_Wireframe.setChecked(False)

    def rougheningChanged(self, v):
        # possible value is a power of 2
        self.spinBox_Roughening.setSingleStep(v)
        self.spinBox_Roughening.setMinimum(max(v // 2, 1))

    def properties(self):
        p = PropertyPage.properties(self)

        try:
            p["comboBox_TextureSize"] = int(p["comboBox_TextureSize"])
        except ValueError:
            p["comboBox_TextureSize"] = "Map Canvas Width"

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

    def __init__(self, parent=None):
        PropertyPage.__init__(self, PAGE_VECTOR, parent)
        Ui_VectorPropertiesWidget.setupUi(self, self)

        self.layer = None
        self.hasZ = self.hasM = False

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
        widgets += [self.checkBox_Visible, self.checkBox_Clickable]
        self.registerPropertyWidgets(widgets)

        self.comboBox_ObjectType.currentIndexChanged.connect(self.setupStyleWidgets)
        self.comboBox_altitudeMode.currentIndexChanged.connect(self.altitudeModeChanged)
        for btn in self.buttonGroup_altitude.buttons():
            btn.toggled.connect(self.zValueRadioButtonToggled)
        self.checkBox_ExportAttrs.toggled.connect(self.exportAttrsToggled)

    def setup(self, layer, mapTo3d):
        self.layer = layer
        self.mapTo3d = mapTo3d
        mapLayer = layer.mapLayer
        properties = layer.properties

        for i in range(self.STYLE_MAX_COUNT):
            self.styleWidgets[i].hide()

        # set up object type combo box
        self.comboBox_ObjectType.blockSignals(True)
        self.comboBox_ObjectType.clear()

        for obj_type in ObjectType.typesByGeomType(mapLayer.geometryType()):
            self.comboBox_ObjectType.addItem(obj_type.displayName(), obj_type.name)

        if properties:
            # restore object type selection
            objType = properties.get("comboBox_ObjectType")

            # for backward compatibility
            if objType == "Profile":
                objType = "Wall"
            elif objType == "Triangular Mesh":
                objType = "Polygon"

            idx = self.comboBox_ObjectType.findData(objType)
            if idx != -1:
                self.comboBox_ObjectType.setCurrentIndex(idx)

        self.comboBox_ObjectType.blockSignals(False)

        # set up altitude mode combo box
        self.comboBox_altitudeMode.blockSignals(True)
        self.comboBox_altitudeMode.clear()
        self.comboBox_altitudeMode.addItem("Absolute")

        # DEM layers
        for lyr in tools.getDEMLayersInProject():
            self.comboBox_altitudeMode.addItem('Relative to "{0}" layer'.format(lyr.name()), lyr.id())

        # DEM provider plugins
        for plugin in pluginManager().demProviderPlugins():
            self.comboBox_altitudeMode.addItem('Relative to "{0}"'.format(plugin.providerName()), "plugin:" + plugin.providerId())

        self.comboBox_altitudeMode.blockSignals(False)

        # set up z/m button
        wkbType = mapLayer.wkbType()
        self.hasZ = wkbType in [QgsWkbTypes.Point25D, QgsWkbTypes.LineString25D, QgsWkbTypes.Polygon25D,
                                QgsWkbTypes.MultiPoint25D, QgsWkbTypes.MultiLineString25D, QgsWkbTypes.MultiPolygon25D]
        self.hasZ = self.hasZ or (wkbType // 1000 in [1, 3])
        self.hasM = (wkbType // 1000 in [2, 3])
        self.radioButton_zValue.setEnabled(self.hasZ)
        self.radioButton_mValue.setEnabled(self.hasM)

        if self.hasZ:
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
            self.labelHeightWidget.setup(options={"layer": mapLayer, "defaultValue": int(defaultLabelHeight / mapTo3d.multiplierZ)})
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
        geomType = self.layer.mapLayer.geometryType()
        obj_type = ObjectType.typeByName(self.comboBox_ObjectType.currentData(), geomType)

        if geomType == QgsWkbTypes.PolygonGeometry:
            supportZM = (obj_type == ObjectType.Polygon)
            self.radioButton_zValue.setEnabled(self.hasZ and supportZM)
            self.radioButton_mValue.setEnabled(self.hasM and supportZM)
            if self.hasZ and supportZM:
                self.radioButton_zValue.setChecked(True)
            elif not supportZM:
                self.radioButton_Expression.setChecked(True)

            self.checkBox_Clip.setVisible(not supportZM)

        obj_type.setupWidgets(self,
                              self.mapTo3d,         # to calculate default values
                              self.layer.mapLayer)

        self.altitudeModeChanged(self.comboBox_altitudeMode.currentIndex())

    def itemChanged(self, item):
        self.setEnabled(item.data(0, Qt.CheckStateRole) == Qt.Checked)

    def altitudeModeChanged(self, index):
        name = self.comboBox_ObjectType.currentData()
        only_clipped = False

        if name == "Overlay" and index:   # Overlay + relative to a DEM layer
            only_clipped = True
            self.radioButton_IntersectingFeatures.setChecked(True)
            self.checkBox_Clip.setChecked(True)

        self.groupBox_Features.setEnabled(not only_clipped)

    def zValueRadioButtonToggled(self, toggled=None):
        if toggled:
            self.label_zExpression.setText("" if self.radioButton_Expression.isChecked() else "Addend")

    def exportAttrsToggled(self, checked):
        self.setLayoutEnabled(self.formLayout_Label, checked)
        self.labelHeightWidget.setEnabled(checked)

    def properties(self):
        return PropertyPage.properties(self)

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


class PointCloudPropertyPage(PropertyPage, Ui_PCPropertiesWidget):

    def __init__(self, parent=None):
        PropertyPage.__init__(self, PAGE_POINTCLOUD, parent)
        Ui_PCPropertiesWidget.setupUi(self, self)

        widgets = [self.url, self.comboBox_ColorType, self.colorButton_Color, self.spinBox_Opacity, self.checkBox_BoxVisible, self.checkBox_Visible]
        self.registerPropertyWidgets(widgets)

        color_types = ["RGB", "COLOR", "HEIGHT", "INTENSITY", "INTENSITY_GRADIENT", "POINT_INDEX", "CLASSIFICATION", "RETURN_NUMBER"]
        # ["RGB", "COLOR", "DEPTH", "HEIGHT", "INTENSITY", "INTENSITY_GRADIENT", "LOD", "POINT_INDEX",
        #  "CLASSIFICATION", "RETURN_NUMBER", "SOURCE", "NORMAL", "PHONG", "RGB_HEIGHT", "COMPOSITE"]

        for t in color_types:
            self.comboBox_ColorType.addItem(t, t)

        self.comboBox_ColorType.currentIndexChanged.connect(self.colorTypeChanged)
        self.colorTypeChanged()

    def setup(self, layer):
        self.lineEdit_Name.setText(layer.name)
        self.setProperties(layer.properties)

        wnd = self.parent().parent()
        loaded = wnd.runScript("app.scene.mapLayers[{}].loadedPointCount()".format(layer.jsLayerId))
        visible = wnd.runScript("app.scene.mapLayers[{}].pcg.children[0].numVisiblePoints".format(layer.jsLayerId))

        total = bbox = None

        url = layer.properties.get("url", "")
        if url.startswith("file:") and url.endswith(("cloud.js", "ept.json")):
            try:
                with open(QUrl(url).toLocalFile(), "r") as f:
                    d = json.load(f)

                total = d.get("points")
                bbox = d.get("tightBoundingBox")        # potree
                if bbox:
                    bbox = [bbox.get("lx"), bbox.get("ly"), bbox.get("lz"), bbox.get("ux"), bbox.get("uy"), bbox.get("uz")]
                else:
                    bbox = d.get("boundsConforming")    # ept
            except:
                pass

        html = "<style>th {text-align:left;padding-right:10px;}</style><table>"
        html += "<tr><th>Point count</th><td>{}</td></tr>".format("Unknown" if total is None else "{:,}".format(int(total)))
        html += "<tr><th>Loaded point count</th><td>{}</td></tr>".format("Unknown" if loaded is None else "{:,}".format(int(loaded)))
        html += "<tr><th>Visible point count</th><td>{}</td></tr>".format("Unknown" if visible is None else "{:,}".format(int(visible)))

        if bbox:
            html += """
<tr><th>Bounding box:</ht><td>{:.3f}, {:.3f}, {:.3f} :<br>{:.3f}, {:.3f}, {:.3f}</td></tr>
""".format(*bbox)

        html += "</table>"
        self.textBrowser.setHtml(html)

    def properties(self):
        p = PropertyPage.properties(self)
        return p

    def colorTypeChanged(self, index=None):
        b = (self.comboBox_ColorType.currentData() == "COLOR")
        self.label_Color.setEnabled(b)
        self.colorButton_Color.setEnabled(b)
