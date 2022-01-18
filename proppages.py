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
from PyQt5.QtWidgets import (QAbstractItemView, QAction, QActionGroup, QCheckBox, QComboBox, QFileDialog, QGroupBox, QLineEdit,
                             QListWidgetItem, QMenu, QMessageBox, QRadioButton, QSlider, QSpinBox, QToolTip, QWidget)
from PyQt5.QtGui import QColor, QCursor
from qgis.core import Qgis, QgsApplication, QgsCoordinateTransform, QgsFieldProxyModel, QgsMapLayer, QgsProject, QgsWkbTypes
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

from . import q3dconst
from .conf import DEBUG_MODE, DEF_SETS
from .datamanager import MaterialManager
from .mapextent import MapExtent
from .pluginmanager import pluginManager
from .q3dcore import calculateGridSegments
from .q3dconst import LayerType, DEMMtlType
from .tools import createUid, getLayersInProject, logMessage
from .propwidget import PropertyWidget
from . import tools
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

    def __init__(self, parent, pageType):
        QWidget.__init__(self, parent)
        self.dialog = parent
        self.pageType = pageType
        self.propertyWidgets = []

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

    def properties(self, widgets=None, only_visible=False):
        widgets = widgets or self.propertyWidgets

        p = {}
        for w in widgets:
            if only_visible and not w.isVisible():
                continue

            v = None
            if isinstance(w, QComboBox):
                v = w.currentData()
                if v is None and w.isEditable():
                    v = w.currentText()
            elif isinstance(w, QRadioButton):
                if not w.isChecked():
                    continue
                v = w.isChecked()
            elif isinstance(w, (QCheckBox, QGroupBox)):
                v = w.isChecked()
            elif isinstance(w, (QSlider, QSpinBox)):
                v = w.value()
            elif isinstance(w, QLineEdit):
                v = w.text()
            elif isinstance(w, PropertyWidget):
                v = w.values()
            elif isinstance(w, QgsFieldExpressionWidget):
                v = w.expression()
            elif isinstance(w, QgsColorButton):
                v = w.color().name().replace("#", "0x")
            else:
                logMessage("[proppages.py] Not recognized widget type: " + str(type(w)))

            p[w.objectName()] = v

        return p

    def setProperties(self, properties):
        for w in self.propertyWidgets:
            v = properties.get(w.objectName())
            if v is None:
                continue

            if isinstance(w, QComboBox):
                index = w.findData(v)
                if index != -1:
                    w.setCurrentIndex(index)
                elif w.isEditable():
                    w.setEditText(str(v))

            elif isinstance(w, (QRadioButton, QCheckBox, QGroupBox)):
                w.setChecked(v)

            elif isinstance(w, (QSlider, QSpinBox)):
                w.setValue(v)

            elif isinstance(w, QLineEdit):
                w.setText(v)
                w.setCursorPosition(0)

            elif isinstance(w, PropertyWidget):
                if len(v):
                    w.setValues(v)

            elif isinstance(w, QgsFieldExpressionWidget):
                w.setExpression(v)

            elif isinstance(w, QgsColorButton):
                w.setColor(QColor(v.replace("0x", "#")))


class ScenePropertyPage(PropertyPage, Ui_ScenePropertiesWidget):

    def __init__(self, parent, properties, canvas):
        PropertyPage.__init__(self, parent, PAGE_SCENE)
        Ui_ScenePropertiesWidget.setupUi(self, self)

        self.mapSettings = canvas.mapSettings()

        widgets = [self.comboBox_xyShift, self.radioButton_FixedExtent, self.lineEdit_CenterX, self.lineEdit_CenterY,
                   self.lineEdit_Width, self.lineEdit_Height, self.lineEdit_Rotation, self.checkBox_FixAspectRatio,
                   self.lineEdit_zFactor, self.lineEdit_zShift, self.checkBox_autoZShift,
                   self.comboBox_MaterialType, self.checkBox_Outline,
                   self.radioButton_Color, self.colorButton_Color,
                   self.groupBox_Fog, self.colorButton_Fog, self.horizontalSlider_Fog,
                   self.radioButton_WGS84, self.radioButton_NoCoords]
        self.registerPropertyWidgets(widgets)

        # 3D world coordinates
        self.comboBox_xyShift.addItem("Automatic", None)
        self.comboBox_xyShift.addItem("Shift to origin", True)
        self.comboBox_xyShift.addItem("No shift", False)

        # 2D map extent
        self.radioButton_FixedExtent.toggled.connect(self.fixedExtentToggled)
        self.lineEdit_Width.editingFinished.connect(self.widthEditingFinished)
        self.pushButton_SelectExtent.clicked.connect(self.showSelectExtentMenu)
        self.checkBox_FixAspectRatio.toggled.connect(self.fixAspectRatioToggled)

        if self.radioButton_UseCanvasExtent.isChecked():
            self.fixedExtentToggled(False)

        if HAVE_PROCESSING:
            self.initMapTool(canvas)

        # material type
        self.comboBox_MaterialType.addItem("Lambert Material", MaterialManager.MESH_LAMBERT)
        self.comboBox_MaterialType.addItem("Phong Material", MaterialManager.MESH_PHONG)
        self.comboBox_MaterialType.addItem("Toon Material", MaterialManager.MESH_TOON)

        # restore properties
        if properties:
            self.setProperties(properties)
        else:
            self.radioButton_UseCanvasExtent.setChecked(True)
            self.lineEdit_zFactor.setText(str(DEF_SETS.Z_EXAGGERATION))
            self.lineEdit_zShift.setText(str(DEF_SETS.Z_SHIFT))
            self.checkBox_autoZShift.setChecked(DEF_SETS.AUTO_Z_SHIFT)
            self.colorButton_Fog.setColor(QColor(Qt.white))

        # supported projections
        # https://github.com/proj4js/proj4js
        projs = ["longlat", "merc"]
        projs += ["aea", "aeqd", "cass", "cea", "eqc", "eqdc", "etmerc", "geocent", "gnom", "krovak", "laea", "lcc", "mill", "moll",
                  "nzmg", "omerc", "ortho", "poly", "qsc", "robin", "sinu", "somerc", "stere", "sterea", "tmerc", "tpers", "utm", "vandg"]

        crs = QgsProject.instance().crs()
        proj = crs.toProj4() if Qgis.QGIS_VERSION_INT < 31003 else crs.toProj()
        m = re.search(r"\+proj=(\w+)", proj)
        proj_supported = bool(m and m.group(1) in projs)

        if not proj_supported and not self.radioButton_NoCoords.isChecked():
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

    def properties(self, only_visible=False):
        p = PropertyPage.properties(self, only_visible=only_visible)
        # check validity
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
        extent = MapExtent(r.center(), r.width(), r.height(), self.canvas.mapSettings().rotation())  # get current map settings
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

    # item data role for material list widget
    MTL_ID = Qt.UserRole
    MTL_PROPERTIES = Qt.UserRole + 1
    MTL_LAYERIDS = Qt.UserRole + 2

    def __init__(self, parent, layer, settings, mapSettings):
        PropertyPage.__init__(self, parent, PAGE_DEM)
        Ui_DEMPropertiesWidget.setupUi(self, self)

        self.layer = layer
        self.extent = settings.baseExtent()
        self.mapSettings = mapSettings

        self.isPlane = bool(layer.layerId.startswith("fp:"))

        widgets = []
        if self.isPlane:
            widgets += [self.lineEdit_Altitude]
        else:
            widgets += [self.horizontalSlider_DEMSize, self.spinBox_Roughening]
            widgets += [self.checkBox_Clip, self.comboBox_ClipLayer]

        widgets += [self.checkBox_Tiles, self.spinBox_Size]
        widgets += [self.spinBox_Opacity, self.checkBox_TransparentBackground, self.lineEdit_ImageFile, self.colorButton_Color, self.comboBox_TextureSize, self.checkBox_Shading]
        widgets += [self.checkBox_Sides, self.toolButton_SideColor, self.lineEdit_Bottom,
                    self.checkBox_Frame, self.toolButton_EdgeColor,
                    self.checkBox_Wireframe, self.toolButton_WireframeColor, self.checkBox_Visible, self.checkBox_Clickable]

        self.registerPropertyWidgets(widgets)

        # geometry group
        if self.isPlane:
            self.setLayoutVisible(self.horizontalLayout_Resampling, False)
            self.setLayoutVisible(self.verticalLayout_Clip, False)
            self.setWidgetsEnabled([self.label_Roughness, self.spinBox_Roughening], False)
        else:
            self.setLayoutVisible(self.formLayout_Altitude, False)

        self.initLayerComboBox()

        self.spinBox_Size.findChild(QLineEdit).setReadOnly(True)
        self.spinBox_Roughening.findChild(QLineEdit).setReadOnly(True)

        self.horizontalSlider_DEMSize.valueChanged.connect(self.resolutionSliderChanged)
        self.checkBox_Tiles.toggled.connect(self.tilesToggled)
        self.checkBox_Clip.toggled.connect(self.clipToggled)
        self.spinBox_Roughening.valueChanged.connect(self.rougheningChanged)

        # material group
        self.mtlPropertiesWidgets = [self.comboBox_TextureSize, self.lineEdit_ImageFile, self.colorButton_Color,
                                     self.spinBox_Opacity, self.checkBox_TransparentBackground, self.checkBox_Shading]

        self.toolButton_AddMtl.setIcon(QgsApplication.getThemeIcon("symbologyAdd.svg"))
        self.toolButton_RemoveMtl.setIcon(QgsApplication.getThemeIcon("symbologyRemove.svg"))

        self.mtlAddActions = []
        self.mtlAddActionGroup = QActionGroup(self)
        for text in ["Layer Image", "Map Canvas Image", "Image File", "Solid Color"]:
            a = QAction(text, self)
            self.mtlAddActions.append(a)
            self.mtlAddActionGroup.addAction(a)

        self.mtlAddActionGroup.triggered.connect(self.addMaterial)

        self.contextMenuAddMtl = QMenu(self)
        self.contextMenuAddMtl.addActions(self.mtlAddActions)

        self.mtlRenameAction = QAction("Rename", self)
        self.mtlRenameAction.triggered.connect(self.renameMtlItem)

        self.contextMenuMtl = QMenu(self)
        self.contextMenuMtl.addAction(self.mtlRenameAction)

        self.comboBox_TextureSize.addItems(["512", "1024", "2048", "4096"])

        self.toolButton_AddMtl.clicked.connect(lambda: self.contextMenuAddMtl.popup(QCursor.pos()))
        self.toolButton_RemoveMtl.clicked.connect(self.removeMaterial)

        self.listWidget_Materials.setDragDropMode(QAbstractItemView.InternalMove)
        self.listWidget_Materials.setDefaultDropAction(Qt.MoveAction)
        self.listWidget_Materials.setContextMenuPolicy(Qt.CustomContextMenu)
        self.listWidget_Materials.customContextMenuRequested.connect(lambda: self.contextMenuMtl.popup(QCursor.pos()))
        self.listWidget_Materials.currentItemChanged.connect(self.materialItemChanged)

        self.toolButton_SelectLayer.clicked.connect(self.showLayerSelectDialog)
        self.toolButton_ImageFile.clicked.connect(self.browseClicked)

        # restore properties
        properties = layer.properties

        properties["checkBox_Sides"] = properties.get("checkBox_Sides", not self.isPlane)
        properties["toolButton_SideColor"] = properties.get("toolButton_SideColor", DEF_SETS.SIDE_COLOR)
        properties["toolButton_EdgeColor"] = properties.get("toolButton_EdgeColor", DEF_SETS.EDGE_COLOR)                   # added in 2.6
        properties["toolButton_WireframeColor"] = properties.get("toolButton_WireframeColor", DEF_SETS.WIREFRAME_COLOR)    # added in 2.6
        properties["lineEdit_Bottom"] = properties.get("lineEdit_Bottom", str(DEF_SETS.Z_BOTTOM))                               # added in 2.7

        self.setProperties(properties)

        # set enablement and visibility of widgets
        self.tilesToggled(self.checkBox_Tiles.isChecked())
        self.comboBox_ClipLayer.setVisible(self.checkBox_Clip.isChecked())

    def initLayerComboBox(self):
        # list of polygon layers
        self.comboBox_ClipLayer.blockSignals(True)
        self.comboBox_ClipLayer.clear()
        for mapLayer in getLayersInProject():
            if mapLayer.type() == QgsMapLayer.VectorLayer and mapLayer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.comboBox_ClipLayer.addItem(mapLayer.name(), mapLayer.id())

        self.comboBox_ClipLayer.blockSignals(False)

    def resolutionSliderChanged(self, v):
        resolutionLevel = self.horizontalSlider_DEMSize.value()
        roughness = self.spinBox_Roughening.value() if self.checkBox_Tiles.isChecked() else 0
        gridSegments = calculateGridSegments(self.extent, resolutionLevel, roughness)

        tip = """Level: {0}
Grid Segments: {1} x {2}
Grid Spacing: {3:.5f} x {4:.5f}{5}"""

        tip = tip.format(resolutionLevel,
                         gridSegments.width(), gridSegments.height(),
                         self.extent.width() / gridSegments.width(),
                         self.extent.height() / gridSegments.height(),
                         "" if self.extent.width() == self.extent.height() else " (Approx.)")
        QToolTip.showText(self.horizontalSlider_DEMSize.mapToGlobal(QPoint(0, 0)), tip, self.horizontalSlider_DEMSize)

    def showLayerSelectDialog(self, item=None):
        item = item or self.listWidget_Materials.currentItem()
        if not item:
            return

        from .layerselectdialog import LayerSelectDialog

        dialog = LayerSelectDialog(self)
        dialog.initTree(item.data(self.MTL_LAYERIDS) or [])
        dialog.setMapSettings(self.mapSettings)
        if not dialog.exec_():
            return

        ids = [layer.id() for layer in dialog.visibleLayers()]
        item.setData(self.MTL_LAYERIDS, ids)
        self.updateLayerImageLabel(ids)

    def updateLayerImageLabel(self, layerIds):
        self.label_LayerImage.setText(tools.shortTextFromSelectedLayerIds(layerIds))

    def browseClicked(self):
        directory = os.path.split(self.lineEdit_ImageFile.text())[0]
        if directory == "":
            directory = QDir.homePath()
        filterString = "Images (*.png *.jpg *.gif *.bmp);;All files (*.*)"
        filename, _ = QFileDialog.getOpenFileName(self, "Select image file", directory, filterString)
        if filename:
            self.lineEdit_ImageFile.setText(filename)

    def tilesToggled(self, checked):
        self.setLayoutVisible(self.gridLayout_Tiles, checked)
        self.setLayoutEnabled(self.verticalLayout_Clip, not checked)

        if checked:
            self.checkBox_Clip.setChecked(False)

    def clipToggled(self, checked):
        if checked:
            self.checkBox_Frame.setChecked(False)
            self.checkBox_Wireframe.setChecked(False)

    def rougheningChanged(self, v):
        # possible value is a power of 2
        self.spinBox_Roughening.setSingleStep(v)
        self.spinBox_Roughening.setMinimum(max(v // 2, 1))

    def properties(self, only_visible=False):
        p = PropertyPage.properties(self, only_visible=only_visible)
        p["materials"] = self.materials()
        mtlItem = self.listWidget_Materials.currentItem()
        if mtlItem:
            p["mtlId"] = mtlItem.data(Qt.UserRole)
        return p

    def setProperties(self, properties):
        PropertyPage.setProperties(self, properties)

        self.setMaterials(properties.get("materials", []))

        id = properties.get("mtlId")
        if id:
            self.setCurrentMtlItem(id)
        else:
            self.listWidget_Materials.setCurrentRow(0)

    def materials(self):
        self.materialItemChanged(None, self.listWidget_Materials.currentItem())  # update current item data

        mtls = []
        for row in range(self.listWidget_Materials.count()):
            item = self.listWidget_Materials.item(row)

            d = {
                "id": item.data(self.MTL_ID),
                "name": item.text(),
                "type": item.type(),
                "properties": item.data(self.MTL_PROPERTIES) or {}
            }

            if item.type() == DEMMtlType.LAYER:
                d["layerIds"] = item.data(self.MTL_LAYERIDS) or []

            mtls.append(d)

        if mtls:
            return mtls

        self.addMaterial()
        return self.materials()

    def setMaterials(self, materials):
        self.listWidget_Materials.clear()

        for mtl in materials:
            item = QListWidgetItem(mtl.get("name", ""), self.listWidget_Materials, mtl.get("type", DEMMtlType.MAPCANVAS))
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled)
            item.setData(self.MTL_ID, mtl.get("id"))
            item.setData(self.MTL_PROPERTIES, mtl.get("properties"))
            ids = mtl.get("layerIds")
            if ids:
                item.setData(self.MTL_LAYERIDS, ids)

    def addMaterial(self, action=None):
        mtype = self.mtlAddActions.index(action) if action else DEMMtlType.MAPCANVAS

        name = {
            DEMMtlType.LAYER: "Layer Image",
            DEMMtlType.MAPCANVAS: "Map Image",
            DEMMtlType.FILE: "Image File",
            DEMMtlType.COLOR: "Solid Color"
        }.get(mtype, "")

        p = {
            "spinBox_Opacity": 100,
            "checkBox_TransparentBackground": False,
            "checkBox_Shading": True
        }

        if mtype in (DEMMtlType.LAYER, DEMMtlType.MAPCANVAS):
            p["comboBox_TextureSize"] = DEF_SETS.TEXTURE_SIZE

        item = QListWidgetItem(name, self.listWidget_Materials, mtype)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsEnabled)
        item.setData(self.MTL_ID, createUid())
        item.setData(self.MTL_PROPERTIES, p)

        if action:
            self.listWidget_Materials.setCurrentItem(item)

            if mtype == DEMMtlType.LAYER:
                self.showLayerSelectDialog(item)

        return item

    def removeMaterial(self):
        row = self.listWidget_Materials.currentRow()
        if row >= 0:
            item = self.listWidget_Materials.item(row)
            msg = "Are you sure you want to remove this material '{}'?".format(item.text())
            if QMessageBox.question(self, "Qgis2threejs", msg) == QMessageBox.Yes:
                self.listWidget_Materials.takeItem(row)

    def renameMtlItem(self):
        item = self.listWidget_Materials.currentItem()
        if item:
            self.listWidget_Materials.editItem(item)

    def setCurrentMtlItem(self, id):
        for row in range(self.listWidget_Materials.count()):
            if self.listWidget_Materials.item(row).data(Qt.UserRole) == id:
                self.listWidget_Materials.setCurrentRow(row)
                return

    def materialItemChanged(self, current, previous):

        if previous:
            previous.setData(self.MTL_PROPERTIES, PropertyPage.properties(self, self.mtlPropertiesWidgets))

        if not current:
            return

        PropertyPage.setProperties(self, current.data(self.MTL_PROPERTIES) or {})

        mtype = current.type()
        if mtype == DEMMtlType.LAYER:
            self.updateLayerImageLabel(current.data(self.MTL_LAYERIDS) or [])

        if previous and previous.type() == mtype:
            return

        # set up widgets for current material type
        layers = image_size = image_file = color = tb = False
        if mtype == DEMMtlType.LAYER:
            layers = image_size = tb = True

        elif mtype == DEMMtlType.MAPCANVAS:
            image_size = tb = True

        elif mtype == DEMMtlType.FILE:
            image_file = tb = True

        else:       # q3dconst.MTL_COLOR:
            color = True

        self.setWidgetsVisible([self.label_Layers, self.label_LayerImage, self.toolButton_SelectLayer], layers)
        self.setWidgetsVisible([self.label_TextureSize, self.comboBox_TextureSize], image_size)
        self.setWidgetsVisible([self.label_ImageFile, self.lineEdit_ImageFile, self.toolButton_ImageFile], image_file)
        self.setWidgetsVisible([self.label_Color, self.colorButton_Color], color)
        self.setWidgetsVisible([self.checkBox_TransparentBackground], tb)
        #TODO: enable shading
        if mtype != DEMMtlType.COLOR:
            self.checkBox_TransparentBackground.setText("Enable transparency" if mtype == DEMMtlType.FILE else "Transparent background")


class VectorPropertyPage(PropertyPage, Ui_VectorPropertiesWidget):

    def __init__(self, parent, layer, settings):
        PropertyPage.__init__(self, parent, PAGE_VECTOR)
        Ui_VectorPropertiesWidget.setupUi(self, self)

        self.layer = layer
        self.settings = settings
        self.mapTo3d = settings.mapTo3d()

        self.hasZ = self.hasM = False

        mapLayer = layer.mapLayer
        properties = layer.properties

        # object type
        for objType in ObjectType.typesByGeomType(layer.type):
            self.comboBox_ObjectType.addItem(objType.displayName(), objType.name)

        if properties:
            objType = properties.get("comboBox_ObjectType")

            idx = self.comboBox_ObjectType.findData(objType)
            if idx != -1:
                self.comboBox_ObjectType.setCurrentIndex(idx)

        # [z coordinate]
        # mode combobox
        self.comboBox_altitudeMode.addItem("Absolute")

        for lyr in tools.getDEMLayersInProject():
            self.comboBox_altitudeMode.addItem('Relative to "{0}" layer'.format(lyr.name()), lyr.id())

        for plugin in pluginManager().demProviderPlugins():
            self.comboBox_altitudeMode.addItem('Relative to "{0}"'.format(plugin.providerName()), "plugin:" + plugin.providerId())

        # z/m buttons
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

        # expression
        self.fieldExpressionWidget_altitude.setFilters(QgsFieldProxyModel.Numeric)
        self.fieldExpressionWidget_altitude.setLayer(mapLayer)
        self.fieldExpressionWidget_altitude.setExpression("0")

        # [geometry]
        self.geomWidgets = []
        for i in range(q3dconst.GEOM_WIDGET_MAX_COUNT):
            name = "geomWidget{}".format(i)

            w = PropertyWidget(self.groupBox_Geometry)
            w.setObjectName(name)

            self.geomWidgets.append(w)
            self.verticalLayout_Geometry.addWidget(w)

        # [material]
        self.comboEdit_Color.setup(PropertyWidget.COLOR, mapLayer)
        self.comboEdit_Color2.setup(PropertyWidget.OPTIONAL_COLOR, mapLayer)
        self.comboEdit_Opacity.setup(PropertyWidget.OPACITY, mapLayer)

        self.mtlWidgets = []
        for i in range(q3dconst.MTL_WIDGET_MAX_COUNT):
            name = "mtlWidget{}".format(i)

            w = PropertyWidget(self.groupBox_Material)
            w.setObjectName(name)

            self.mtlWidgets.append(w)
            self.verticalLayout_Material.addWidget(w)

        # [features]
        # point layer has no geometry clip option
        self.checkBox_Clip.setVisible(layer.type != LayerType.POINT)

        # [label]
        hasRPt = (layer.type in (LayerType.POINT, LayerType.POLYGON))
        if hasRPt:
            self.comboBox_Label.addItem("(No label)")
            fields = mapLayer.fields()
            for i in range(fields.count()):
                self.comboBox_Label.addItem(fields[i].name(), i)

            defaultLabelHeight = 5
            self.labelHeightWidget.setup(PropertyWidget.LABEL_HEIGHT, mapLayer, {"defaultValue": int(defaultLabelHeight / self.mapTo3d.zScale)})

        self.exportAttrsToggled(bool(hasRPt and properties.get("checkBox_ExportAttrs")))

        # register widgets
        widgets = [self.comboBox_ObjectType]
        widgets += self.buttonGroup_altitude.buttons() + [self.comboBox_altitudeMode, self.fieldExpressionWidget_altitude, self.comboEdit_altitude2]
        widgets += [self.comboEdit_FilePath]
        widgets += self.geomWidgets
        widgets += [self.comboEdit_Color, self.comboEdit_Color2, self.comboEdit_Opacity] + self.mtlWidgets
        widgets += [self.radioButton_AllFeatures, self.radioButton_IntersectingFeatures, self.checkBox_Clip]
        widgets += [self.checkBox_ExportAttrs, self.comboBox_Label, self.labelHeightWidget]
        widgets += [self.checkBox_Visible, self.checkBox_Clickable]
        self.registerPropertyWidgets(widgets)

        self.comboBox_ObjectType.currentIndexChanged.connect(self.objectTypeChanged)
        self.comboBox_altitudeMode.currentIndexChanged.connect(self.altitudeModeChanged)
        for btn in self.buttonGroup_altitude.buttons():
            btn.toggled.connect(self.zValueRadioButtonToggled)
        self.checkBox_ExportAttrs.toggled.connect(self.exportAttrsToggled)

        # set up widgets for selected object type
        self.objectTypeChanged()

        # restore other properties for the layer
        self.setProperties(properties or {})

    def objectTypeChanged(self, index=None):
        obj_type = ObjectType.typeByName(self.comboBox_ObjectType.currentData(), self.layer.type)(self.settings)

        if self.layer.type == LayerType.POLYGON:
            supportZM = (obj_type == ObjectType.Polygon)
            self.radioButton_zValue.setEnabled(self.hasZ and supportZM)
            self.radioButton_mValue.setEnabled(self.hasM and supportZM)
            if self.hasZ and supportZM:
                self.radioButton_zValue.setChecked(True)
            elif not supportZM:
                self.radioButton_Expression.setChecked(True)

            self.checkBox_Clip.setVisible(not supportZM)

        obj_type.setupWidgets(self)

        self.altitudeModeChanged(self.comboBox_altitudeMode.currentIndex())

    def setupWidgets(self, filepath=None, geomItems=None, color=True, color2=None, opacity=True, mtlItems=None, alt2=False):

        self.comboEdit_altitude2.setVisible(alt2)
        if alt2:
            self.comboEdit_altitude2.setup(PropertyWidget.EXPRESSION, self.layer.mapLayer, {"name": "Other side Z"})

        self.groupBox_FilePath.setVisible(bool(filepath))
        if filepath:
            self.comboEdit_FilePath.setup(PropertyWidget.FILEPATH, self.layer.mapLayer, filepath)

        # geometry
        geomItems = geomItems or []
        for i, item in enumerate(geomItems):
            self.geomWidgets[i].setup(item.get("type", PropertyWidget.EXPRESSION), self.layer.mapLayer, item)

        for i in range(q3dconst.GEOM_WIDGET_MAX_COUNT):
            self.geomWidgets[i].setVisible(bool(i < len(geomItems)))

        # material
        self.comboEdit_Color.setVisible(color)

        self.comboEdit_Color2.setVisible(bool(color2))
        if color2:
            self.comboEdit_Color2.setup(PropertyWidget.OPTIONAL_COLOR, self.layer.mapLayer, color2)

        self.comboEdit_Opacity.setVisible(opacity)

        mtlItems = mtlItems or []
        for i, item in enumerate(mtlItems):
            self.mtlWidgets[i].setup(item.get("type", PropertyWidget.EXPRESSION), self.layer.mapLayer, item)

        for i in range(q3dconst.MTL_WIDGET_MAX_COUNT):
            self.mtlWidgets[i].setVisible(bool(i < len(mtlItems)))

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
        if checked and self.layer.type == LayerType.LINESTRING:
            return

        self.setWidgetsVisible([self.label, self.comboBox_Label, self.labelHeightWidget], checked)
        # self.setLayoutVisible(self.gridLayout_Label, checked)   # FIXME: doesn't work correctly...


class PointCloudPropertyPage(PropertyPage, Ui_PCPropertiesWidget):

    def __init__(self, parent, layer):
        PropertyPage.__init__(self, parent, PAGE_POINTCLOUD)
        Ui_PCPropertiesWidget.setupUi(self, self)

        widgets = [self.url, self.comboBox_ColorType, self.colorButton_Color, self.spinBox_Opacity, self.checkBox_BoxVisible, self.checkBox_Visible]
        self.registerPropertyWidgets(widgets)

        self.lineEdit_Name.setText(layer.name)

        color_types = ["RGB", "COLOR", "HEIGHT", "INTENSITY", "INTENSITY_GRADIENT", "POINT_INDEX", "CLASSIFICATION", "RETURN_NUMBER"]
        # ["RGB", "COLOR", "DEPTH", "HEIGHT", "INTENSITY", "INTENSITY_GRADIENT", "LOD", "POINT_INDEX",
        #  "CLASSIFICATION", "RETURN_NUMBER", "SOURCE", "NORMAL", "PHONG", "RGB_HEIGHT", "COMPOSITE"]

        for t in color_types:
            self.comboBox_ColorType.addItem(t, t)

        self.comboBox_ColorType.currentIndexChanged.connect(self.colorTypeChanged)
        self.colorTypeChanged()

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

    def colorTypeChanged(self, index=None):
        b = (self.comboBox_ColorType.currentData() == "COLOR")
        self.label_Color.setEnabled(b)
        self.colorButton_Color.setEnabled(b)
