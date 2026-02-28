# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-03-27

import os
import json
import math
import re

from qgis.PyQt.QtCore import Qt, QPoint, QSize, QUrl
from qgis.PyQt.QtWidgets import (QAbstractItemView, QAction, QActionGroup, QCheckBox, QComboBox, QGroupBox, QLineEdit,
                             QListWidgetItem, QMenu, QMessageBox, QRadioButton, QSlider, QSpinBox, QToolTip, QWidget)
from qgis.PyQt.QtGui import QColor, QCursor, QIcon, QPixmap
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

from .propwidget import PropertyWidget
from ..conf import DEF_SETS, PLUGIN_NAME
from ..core.build.datamanager import MaterialManager
from ..core.build.vector.object import ObjectType
from ..core.const import LayerType, DEMMtlType, GEOM_WIDGET_MAX_COUNT, MTL_WIDGET_MAX_COUNT
from ..core.exportsettings import calculateGridSegments
from ..core.mapextent import MapExtent
from ..core.plugin.pluginmanager import pluginManager
from ..utils import (createUid, getDEMLayersInProject, getLayersInProject, hex_color,
                     logger, shortTextFromSelectedLayerIds)
from ..utils.gui import selectColor, selectImageFile

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


class HiddenProperty:

    def __init__(self, name, val=None):
        self.name = name
        self.value = val
        self.visible = False

    def objectName(self):
        return self.name

    def isVisible(self):
        return self.visible

    def setVisible(self, visible):
        self.visible = visible


class PropertyPage(QWidget):

    def __init__(self, parent, pageType):
        super().__init__(parent)
        self.dialog = parent
        self.pageType = pageType
        self.propertyWidgets = []

    def setLayoutVisible(self, layout, visible):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            w = item.widget()
            if w is not None:
                w.setVisible(visible)
                continue
            lyt = item.layout()
            if lyt is not None:
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

    # collect property widget values into a properties dictionary
    def properties(self, widgets=None):
        widgets = widgets or self.propertyWidgets

        p = {}
        for w in widgets:
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
                c = w.color()
                v = [c.red(), c.green(), c.blue(), c.alpha()]
            elif isinstance(w, HiddenProperty):
                v = w.value
            else:
                logger.warning("[proppages.py] Not recognized widget type: " + str(type(w)))

            p[w.objectName()] = v

        return p

    # restore property widget values from properties dictionary
    def restoreProperties(self, properties, widgets=None):
        widgets = widgets or self.propertyWidgets

        try:
            for w in widgets:
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
                    if isinstance(v, list):
                        w.setColor(QColor(*v))
                    else:
                        w.setColor(QColor(v.replace("0x", "#")))

                elif isinstance(w, HiddenProperty):
                    w.value = v

        except KeyError as _:
            logger.error("Property read error: Unable to fully read properties. The settings file may have been saved with a newer plugin version. If the dialog cannot be opened, please clear the export settings.")
            import traceback
            logger.error(traceback.format_exc())


class ScenePropertyPage(PropertyPage, Ui_ScenePropertiesWidget):

    def __init__(self, parent, properties, canvas):
        PropertyPage.__init__(self, parent, PAGE_SCENE)
        Ui_ScenePropertiesWidget.setupUi(self, self)

        self.mapSettings = canvas.mapSettings()

        widgets = [self.comboBox_xyShift, self.radioButton_FixedExtent, self.lineEdit_CenterX, self.lineEdit_CenterY,
                   self.lineEdit_Width, self.lineEdit_Height, self.lineEdit_Rotation, self.checkBox_FixAspectRatio,
                   self.lineEdit_zFactor,
                   self.radioButton_Color, self.colorButton_Color,
                   self.groupBox_Fog, self.colorButton_Fog, self.slider_Fog,
                   self.radioButton_PtLight,
                   self.comboBox_MaterialType, self.checkBox_Outline,
                   self.radioButton_WGS84, self.radioButton_NoCoords]
        self.registerPropertyWidgets(widgets)

        # 3D world coordinates
        self.comboBox_xyShift.addItem("Center of base extent", True)
        self.comboBox_xyShift.addItem("Origin of map coordinate system", False)

        self.comboBox_xyShift.setItemData(0, "Shifts the 3D world origin to center of base extent to preserve precision.", Qt.ItemDataRole.ToolTipRole)
        self.comboBox_xyShift.setItemData(1, "Outputs map coordinates without transformation.", Qt.ItemDataRole.ToolTipRole)

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
            self.restoreProperties(properties)
        else:
            self.radioButton_UseCanvasExtent.setChecked(True)
            self.lineEdit_zFactor.setText(str(DEF_SETS.Z_EXAGGERATION))
            self.colorButton_Fog.setColor(QColor(Qt.GlobalColor.white))

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
        global HAVE_PROCESSING
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
        if not is_number(self.lineEdit_zFactor.text()):
            p["lineEdit_zFactor"] = str(DEF_SETS.Z_EXAGGERATION)
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

        popup.exec(QCursor.pos())

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
        if dlg.exec():
            layer = dlg.selectedLayer()

            transform = QgsCoordinateTransform(layer.crs(), self.mapSettings.destinationCrs(), QgsProject.instance())
            r = transform.transformBoundingBox(layer.extent())

            self.checkBox_FixAspectRatio.setChecked(False)

            extent = MapExtent(r.center(), r.width(), r.height())
            self.setExtent(extent)


class DEMPropertyPage(PropertyPage, Ui_DEMPropertiesWidget):

    # item data role for material list widget
    DATA_ID = Qt.ItemDataRole.UserRole
    DATA_PROPERTIES = Qt.ItemDataRole.UserRole + 1       # except for layer ids

    def __init__(self, parent, layer, settings, mapSettings):
        PropertyPage.__init__(self, parent, PAGE_DEM)
        Ui_DEMPropertiesWidget.setupUi(self, self)

        self.layer = layer
        self.extent = settings.baseExtent()
        self.mapSettings = mapSettings

        self.isPlane = bool(layer.layerId.startswith("fp:"))
        self.hasPolygonLayer = False

        widgets = [self.lineEdit_Name]
        # geometry
        if self.isPlane:
            widgets += [self.lineEdit_Altitude]
        else:
            widgets += [self.radioButton_OriginalValues, self.spinBox_TileSideSegments]
            widgets += [self.horizontalSlider_DEMSize, self.spinBox_Roughening]
            widgets += [self.radioButton_ClipPolygon, self.comboBox_ClipLayer, self.radioButton_NoClip]

        widgets += [self.checkBox_Tiles, self.spinBox_Size]

        # others
        widgets += [self.checkBox_Sides, self.colorButton_Side, self.lineEdit_Bottom,
                    self.checkBox_Frame, self.colorButton_Edge]
        if not self.isPlane:
            widgets += [self.checkBox_Wireframe, self.colorButton_Wireframe]

        widgets += [self.checkBox_Visible, self.checkBox_Clickable]

        self.registerPropertyWidgets(widgets)

        # geometry group
        if self.isPlane:
            self.setWidgetsVisible([self.groupBoxResampMethod, self.groupBoxClip], False)
            self.setWidgetsVisible([self.labelRoughness, self.spinBox_Roughening], False)
            self.setWidgetsVisible([self.checkBox_Wireframe, self.colorButton_Wireframe], False)
            self.lineEdit_Altitude.textChanged.connect(self.altitudeChanged)

        else:
            self.setLayoutVisible(self.formLayout_Altitude, False)

            err_msg = self.origValuesErrorMsg()
            if err_msg:
                self.labelOriginalValues.setText("This option is disabled because " + err_msg)
                self.setWidgetsEnabled([self.radioButton_OriginalValues, self.radioButton_NoClip], False)
                self.setWidgetsVisible([self.labelTileSize, self.spinBox_TileSideSegments], False)
            else:
                self.labelOriginalValues.hide()

            self.initLayerComboBox()

            self.spinBox_Size.findChild(QLineEdit).setReadOnly(True)
            self.spinBox_Roughening.findChild(QLineEdit).setReadOnly(True)

            self.radioButton_Resampling.toggled.connect(self.resamplingMethodChanged)
            self.horizontalSlider_DEMSize.valueChanged.connect(self.resolutionSliderChanged)

            self.lineEdit_Name.setPlaceholderText(layer.mapLayer.name() if layer.mapLayer else layer.name)


        self.checkBox_Tiles.toggled.connect(self.tilesToggled)
        self.spinBox_Roughening.valueChanged.connect(self.rougheningChanged)

        # material group
        self.mtlLayerIds = HiddenProperty("layerIds", [])
        self.mtlWidgets = [self.comboBox_TextureSize, self.radioButton_JPEG, self.radioButton_PNG, self.lineEdit_ImageFile, self.colorButton_Color,
                           self.spinBox_Opacity, self.checkBox_TransparentBackground, self.checkBox_Shading,
                           self.mtlLayerIds]

        self.toolButton_AddMtl.setIcon(QgsApplication.getThemeIcon("symbologyAdd.svg"))
        self.toolButton_RemoveMtl.setIcon(QgsApplication.getThemeIcon("symbologyRemove.svg"))

        self.mtlAddActionGroup = QActionGroup(self)
        for i, text in [(DEMMtlType.LAYER, "Select Layer(s)..."),
                        (DEMMtlType.FILE, "Image File..."),
                        (DEMMtlType.COLOR, "Solid Color..."),
                        (DEMMtlType.MAPCANVAS, "Map Canvas Layers")]:

            a = QAction(text, self)
            a.setData(i)
            self.mtlAddActionGroup.addAction(a)

        self.mtlAddActionGroup.triggered.connect(self.addMaterial)

        self.contextMenuAddMtl = QMenu(self)
        self.contextMenuAddMtl.addActions(self.mtlAddActionGroup.actions())

        self.mtlRenameAction = QAction("Rename", self)
        self.mtlRenameAction.triggered.connect(self.renameMtlItem)

        self.contextMenuMtl = QMenu(self)
        self.contextMenuMtl.addAction(self.mtlRenameAction)

        self.comboBox_TextureSize.addItems(["512", "1024", "2048", "4096"])
        self.comboBox_TextureSize.setCurrentText(str(DEF_SETS.TEXTURE_SIZE))

        self.toolButton_AddMtl.clicked.connect(lambda: self.contextMenuAddMtl.popup(QCursor.pos()))
        self.toolButton_RemoveMtl.clicked.connect(self.removeMaterial)

        self.listWidget_Materials.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.listWidget_Materials.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.listWidget_Materials.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.listWidget_Materials.setIconSize(QSize(16, 16))
        self.listWidget_Materials.customContextMenuRequested.connect(lambda: self.contextMenuMtl.popup(QCursor.pos()))
        self.listWidget_Materials.currentItemChanged.connect(self.materialItemChanged)

        self.toolButton_SelectLayer.clicked.connect(self.selectLayer)
        self.toolButton_ImageFile.clicked.connect(self.selectImageFile)
        self.colorButton_Color.colorChanged.connect(self.colorChanged)

        # restore properties
        properties = layer.properties
        properties["colorButton_Side"] = properties.get("colorButton_Side", DEF_SETS.SIDE_COLOR)
        properties["colorButton_Edge"] = properties.get("colorButton_Edge", DEF_SETS.EDGE_COLOR)                   # added in 2.6
        properties["colorButton_Wireframe"] = properties.get("colorButton_Wireframe", DEF_SETS.WIREFRAME_COLOR)    # added in 2.6
        properties["lineEdit_Bottom"] = properties.get("lineEdit_Bottom", str(DEF_SETS.Z_BOTTOM))                  # added in 2.7

        self.restoreProperties(properties)

        if self.isPlane:
            self.altitudeChanged(self.lineEdit_Altitude.text())

        # set enabled and visible state of widgets
        self.resamplingMethodChanged(self.radioButton_Resampling.isChecked())
        self.tilesToggled(self.checkBox_Tiles.isChecked())
        if not self.checkBox_Sides.isChecked():
            self.label_Bottom.setVisible(False)
            self.lineEdit_Bottom.setVisible(False)

    def origValuesErrorMsg(self):
        mapLayer = self.layer.mapLayer
        if not mapLayer:
            return "the map layer doesn't exist."

        if not math.isclose(mapLayer.rasterUnitsPerPixelX(), mapLayer.rasterUnitsPerPixelY()):
            return "pixel size is different in X and Y directions."

        crs1 = mapLayer.crs()
        crs2 = self.mapSettings.destinationCrs()

        if crs1 == crs2:
            return None

        try:
            proj1 = crs1.toProj()
            proj2 = crs2.toProj()
        except AttributeError:      # Qgis.QGIS_VERSION_INT < 31003
            proj1 = crs1.toProj4()
            proj2 = crs2.toProj4()

        if proj1 == proj2:
            return None

        return "layer CRS differs from project CRS."

    def initLayerComboBox(self):
        # polygon layers
        self.comboBox_ClipLayer.clear()
        self.hasPolygonLayer = False
        for mapLayer in getLayersInProject():
            if mapLayer.type() == QgsMapLayer.VectorLayer and mapLayer.geometryType() == QgsWkbTypes.PolygonGeometry:
                self.comboBox_ClipLayer.addItem(mapLayer.name(), mapLayer.id())
                self.hasPolygonLayer = True

        if not self.hasPolygonLayer:
            self.comboBox_ClipLayer.addItem("(no polygon layer)")
            self.radioButton_ClipPolygon.setEnabled(False)

    def altitudeChanged(self, alt):
        self.lineEdit_Name.setPlaceholderText("Flat Plane" + ("" if alt == "0" or alt == "" else f" ({alt})"))

    def resamplingMethodChanged(self, checked):
        resamp = checked
        self.setLayoutEnabled(self.formLayoutOriginalValues, not resamp)
        self.setLayoutEnabled(self.horizontalLayoutResamp, resamp)
        self.radioButton_ClipPolygon.setEnabled(resamp)
        self.radioButton_NoClip.setEnabled(not resamp)

        if not resamp and self.radioButton_ClipPolygon.isChecked():
            self.radioButton_ClipBaseExtent.setChecked(True)

        if resamp and self.radioButton_NoClip.isChecked():
            self.radioButton_ClipBaseExtent.setChecked(True)

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

    def tilesToggled(self, checked):
        self.setLayoutEnabled(self.gridLayoutTiles, checked)
        self.radioButton_ClipPolygon.setEnabled(not checked and self.radioButton_Resampling.isChecked() and self.hasPolygonLayer)

        if checked and self.radioButton_ClipPolygon.isChecked():
            self.radioButton_ClipBaseExtent.setChecked(True)

    def rougheningChanged(self, v):
        # possible value is a power of 2
        self.spinBox_Roughening.setSingleStep(v)
        self.spinBox_Roughening.setMinimum(max(v // 2, 1))

    def selectLayer(self, _checked=False, update=True):
        from .layerselectdialog import LayerSelectDialog

        item = self.listWidget_Materials.currentItem() if update else None

        p = (item.data(self.DATA_PROPERTIES) if item else None) or {}
        ids = p.get("layerIds")

        dialog = LayerSelectDialog(self)
        dialog.initTree(ids)
        dialog.setMapSettings(self.mapSettings)
        if not dialog.exec():
            return None

        ids = dialog.visibleLayerIds()
        if update:
            self.mtlLayerIds.value = ids
            self.updateLayerImageLabel()
            item.setText(self.uniqueMtlName(self.mtlNameFromLayerIds(ids)))
        return ids

    def updateLayerImageLabel(self):
        self.label_LayerImage.setText(shortTextFromSelectedLayerIds(self.mtlLayerIds.value))

    def selectImageFile(self, _checked=False, update=True):
        directory = os.path.split(self.lineEdit_ImageFile.text())[0]
        filename = selectImageFile(self, directory)
        if filename and update:
            self.lineEdit_ImageFile.setText(filename)

            item = self.listWidget_Materials.currentItem()
            if item:
                item.setText(os.path.splitext(os.path.basename(filename))[0])
        return filename

    def colorChanged(self, color):
        item = self.listWidget_Materials.currentItem()
        if item and item.type() == DEMMtlType.COLOR:
            item.setIcon(DEMPropertyPage.iconForColor(color))

    def properties(self):
        p = PropertyPage.properties(self)
        p["materials"] = self.materials()
        mtlItem = self.listWidget_Materials.currentItem()
        if mtlItem:
            p["mtlId"] = mtlItem.data(Qt.ItemDataRole.UserRole)
        return p

    def restoreProperties(self, properties):
        PropertyPage.restoreProperties(self, properties)

        self.restoreMaterials(properties.get("materials", []))

        if not self.listWidget_Materials.count():
            self.addMaterial()

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
                "id": item.data(self.DATA_ID),
                "name": item.text(),
                "type": item.type(),
                "properties": item.data(self.DATA_PROPERTIES) or {}
            }

            mtls.append(d)

        if mtls:
            return mtls

        self.addMaterial()
        return self.materials()

    def restoreMaterials(self, materials):
        self.listWidget_Materials.clear()

        for mtl in materials:
            item = QListWidgetItem(mtl.get("name", ""), self.listWidget_Materials, mtl.get("type", DEMMtlType.MAPCANVAS))
            item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsEnabled)
            item.setData(self.DATA_ID, mtl.get("id"))
            item.setData(self.DATA_PROPERTIES, mtl.get("properties"))
            item.setIcon(DEMPropertyPage.iconForMtl(mtl))

    def mtlNameFromLayerIds(self, mapLayerIds):
        if not mapLayerIds:
            return "empty map"

        layer = QgsProject.instance().mapLayer(mapLayerIds[0])
        if layer:
            name = layer.name()
            n = len(mapLayerIds)
            if n == 1:
                return name
            else:
                return "{} and {} layer{}".format(name, n - 1, "s" if n > 2 else "")

        return "map"

    def uniqueMtlName(self, base_name):
        n = self.listWidget_Materials.count()
        names = [self.listWidget_Materials.item(r).text() for r in range(n)]

        for i in range(n + 1):
            name = base_name
            if i:
                name += " {}".format(i + 1)
            if name not in names:
                return name

    def addMaterial(self, action=None):
        mtype = action.data() if action else DEMMtlType.MAPCANVAS

        p = {
            "spinBox_Opacity": 100,
            "checkBox_Shading": True
        }

        if mtype in (DEMMtlType.LAYER, DEMMtlType.MAPCANVAS):
            if mtype == DEMMtlType.LAYER:
                ids = self.selectLayer(update=False)
                if ids is None:
                    return
                base_name = self.mtlNameFromLayerIds(ids)
                p["layerIds"] = ids
            else:
                base_name = "map (canvas)"

            p["comboBox_TextureSize"] = DEF_SETS.TEXTURE_SIZE
            p["checkBox_TransparentBackground"] = False

        elif mtype == DEMMtlType.FILE:
            filename = self.selectImageFile(update=False)
            if not filename:
                return
            base_name = os.path.splitext(os.path.basename(filename))[0]
            p["lineEdit_ImageFile"] = filename

        else:
            color = selectColor()
            if not color:
                return
            base_name = "color"
            p["colorButton_Color"] = [color.red(), color.green(), color.blue()]

        name = self.uniqueMtlName(base_name)

        item = QListWidgetItem(name, self.listWidget_Materials, mtype)
        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsEnabled)
        item.setData(self.DATA_ID, createUid())
        item.setData(self.DATA_PROPERTIES, p)
        item.setIcon(DEMPropertyPage.iconForMtl({"type": mtype, "properties": p}))

        if action:
            self.listWidget_Materials.setCurrentItem(item)

        return item

    def removeMaterial(self):
        row = self.listWidget_Materials.currentRow()
        if row >= 0:
            item = self.listWidget_Materials.item(row)
            msg = 'Are you sure you want to remove material "{}"?'.format(item.text())
            if QMessageBox.question(self, PLUGIN_NAME, msg) == QMessageBox.StandardButton.Yes:
                self.listWidget_Materials.takeItem(row)

    def renameMtlItem(self):
        item = self.listWidget_Materials.currentItem()
        if item:
            self.listWidget_Materials.editItem(item)

    def setCurrentMtlItem(self, id):
        for row in range(self.listWidget_Materials.count()):
            if self.listWidget_Materials.item(row).data(Qt.ItemDataRole.UserRole) == id:
                self.listWidget_Materials.setCurrentRow(row)
                return

    def materialItemChanged(self, current, previous):
        if previous:
            p = PropertyPage.properties(self, self.mtlWidgets)
            previous.setData(self.DATA_PROPERTIES, p)

        if not current:
            return

        p = current.data(self.DATA_PROPERTIES) or {}
        PropertyPage.restoreProperties(self, p, self.mtlWidgets)

        mtype = current.type()
        if mtype == DEMMtlType.LAYER:
            self.updateLayerImageLabel()

        if previous and previous.type() == mtype:
            return

        # set up widgets for current material type
        layers = image_size = image_file = color = tb = False
        if mtype == DEMMtlType.LAYER:
            layers = image_size = tb = True

        elif mtype == DEMMtlType.MAPCANVAS:
            image_size = tb = True

        elif mtype == DEMMtlType.FILE:
            image_file = True

        else:       # const.MTL_COLOR:
            color = True

        self.setWidgetsVisible([self.label_Layers, self.label_LayerImage, self.toolButton_SelectLayer, self.mtlLayerIds], layers)
        self.setWidgetsVisible([self.label_TextureSize, self.comboBox_TextureSize, self.label_Format, self.radioButton_JPEG, self.radioButton_PNG], image_size)
        self.setWidgetsVisible([self.label_ImageFile, self.lineEdit_ImageFile, self.toolButton_ImageFile], image_file)
        self.setWidgetsVisible([self.label_Color, self.colorButton_Color], color)
        self.setWidgetsVisible([self.checkBox_TransparentBackground], tb)

    @staticmethod
    def iconForMtl(mtl):
        t = mtl.get("type")
        if t == DEMMtlType.COLOR:
            color = mtl.get("properties", {}).get("colorButton_Color")
            if color:
                return DEMPropertyPage.iconForColor(color)
        else:
            p = DEMMtlType.ICON_PATHS.get(t)
            if p:
                return QgsApplication.getThemeIcon(p)

        return QIcon()

    @staticmethod
    def iconForColor(color):
        if not isinstance(color, QColor):
            color = QColor(hex_color(color))
        pixmap = QPixmap(24, 14)
        pixmap.fill(color)
        return QIcon(pixmap)


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

        self.lineEdit_Name.setPlaceholderText(mapLayer.name())

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

        for lyr in getDEMLayersInProject():
            self.comboBox_altitudeMode.addItem('Relative to "{}" layer'.format(lyr.name()), lyr.id())

        for plugin in pluginManager().demProviderPlugins():
            self.comboBox_altitudeMode.addItem('Relative to "{}"'.format(plugin.providerName()), "plugin:" + plugin.providerId())

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
        for i in range(GEOM_WIDGET_MAX_COUNT):
            name = "geomWidget{}".format(i)

            w = PropertyWidget(self.groupBox_Shape)
            w.setObjectName(name)

            self.geomWidgets.append(w)
            self.verticalLayout_Geometry.addWidget(w)

        # [material]
        self.comboEdit_Color.setup(PropertyWidget.COLOR, mapLayer)
        self.comboEdit_Color2.setup(PropertyWidget.OPTIONAL_COLOR, mapLayer)
        self.comboEdit_Opacity.setup(PropertyWidget.OPACITY, mapLayer)

        self.mtlWidgets = []
        for i in range(MTL_WIDGET_MAX_COUNT):
            name = "mtlWidget{}".format(i)

            w = PropertyWidget(self.groupBox_Material)
            w.setObjectName(name)

            self.mtlWidgets.append(w)
            self.verticalLayout_Material.addWidget(w)

        # [features]
        # point layer has no geometry clip option
        self.checkBox_Clip.setVisible(layer.type != LayerType.POINT)

        # [labels]
        hasRPt = (layer.type in (LayerType.POINT, LayerType.POLYGON))
        if hasRPt:
            self.labelToggled(False)

            self.labelHeightWidget.setup(PropertyWidget.LABEL_HEIGHT, mapLayer, {"defVal": DEF_SETS.LABEL_HEIGHT})
            self.labelHeightWidget.label_1.setMinimumWidth(self.label_Text.minimumWidth())

            self.expression_Label.setLayer(mapLayer)
            self.expression_Label.setRow(0)

            for text in ["sans-serif", "serif", "monospace", "cursive", "fantasy"]:
                self.comboBox_FontFamily.addItem(text, text)

            self.slider_FontSize.setValue(3)

            self.colorButton_BgColor.setAllowOpacity(True)

            properties["colorButton_Label"] = properties.get("colorButton_Label", DEF_SETS.LABEL_COLOR)
            properties["colorButton_OtlColor"] = properties.get("colorButton_OtlColor", DEF_SETS.OTL_COLOR)
            properties["colorButton_BgColor"] = properties.get("colorButton_BgColor", DEF_SETS.BG_COLOR)
            properties["colorButton_ConnColor"] = properties.get("colorButton_ConnColor", DEF_SETS.CONN_COLOR)

        else:
            self.tabWidget.removeTab(self.tabWidget.indexOf(self.tabLabel))

        # register widgets
        widgets = [self.lineEdit_Name, self.comboBox_ObjectType]
        widgets += self.buttonGroup_altitude.buttons() + [self.comboBox_altitudeMode, self.fieldExpressionWidget_altitude, self.comboEdit_altitude2]
        widgets += [self.comboEdit_FilePath]
        widgets += self.geomWidgets
        widgets += [self.comboEdit_Color, self.comboEdit_Color2, self.comboEdit_Opacity] + self.mtlWidgets
        widgets += [
            self.radioButton_AllFeatures, self.radioButton_IntersectingFeatures, self.checkBox_Clip, self.checkBox_ExportAttrs,
            self.checkBox_Visible, self.checkBox_Clickable
        ]
        if hasRPt:
            widgets += [
                self.checkBox_Label, self.labelHeightWidget, self.expression_Label, self.comboBox_FontFamily, self.slider_FontSize,
                self.colorButton_Label, self.checkBox_Outline, self.colorButton_OtlColor,
                self.groupBox_Background, self.colorButton_BgColor,
                self.groupBox_Conn, self.colorButton_ConnColor, self.checkBox_Underline
            ]

        self.registerPropertyWidgets(widgets)

        self.comboBox_ObjectType.currentIndexChanged.connect(self.objectTypeChanged)
        self.comboBox_altitudeMode.currentIndexChanged.connect(self.altitudeModeChanged)
        for btn in self.buttonGroup_altitude.buttons():
            btn.toggled.connect(self.zValueRadioButtonToggled)

        self.checkBox_Label.toggled.connect(self.labelToggled)

        # set up widgets for selected object type
        # currentIndexChanged signal is not emitted in restoreProperties() if current item is first item
        self.objectTypeChanged()

        # restore other properties for the layer
        self.restoreProperties(properties or {})

        # update z value expression label
        self.zValueRadioButtonToggled(True)

    def objectTypeChanged(self, index=None):
        objType = ObjectType.typeByName(self.comboBox_ObjectType.currentData(), self.layer.type)

        if self.layer.type == LayerType.LINESTRING:
            self.checkBox_Clickable.setVisible(objType != ObjectType.ThickLine)

        elif self.layer.type == LayerType.POLYGON:
            supportZM = (objType == ObjectType.Polygon)
            self.radioButton_zValue.setEnabled(self.hasZ and supportZM)
            self.radioButton_mValue.setEnabled(self.hasM and supportZM)
            if self.hasZ and supportZM:
                self.radioButton_zValue.setChecked(True)
            elif not supportZM:
                self.radioButton_Expression.setChecked(True)

            self.checkBox_Clip.setVisible(not supportZM)

        objType(self.settings).setupWidgets(self)

        self.altitudeModeChanged(self.comboBox_altitudeMode.currentIndex())

    def setupWidgets(self, filepath=None, geomItems=None, color=True, color2=None, opacity=True, mtlItems=None, alt2=False):

        self.comboEdit_altitude2.setVisible(alt2)
        if alt2:
            self.comboEdit_altitude2.setup(PropertyWidget.EXPRESSION, self.layer.mapLayer, {"name": "Other side Z"})

        self.comboEdit_FilePath.setVisible(bool(filepath))
        if filepath:
            self.comboEdit_FilePath.setup(PropertyWidget.FILEPATH, self.layer.mapLayer, filepath)

        # geometry
        geomItems = geomItems or []
        for i, opt in enumerate(geomItems):
            self.geomWidgets[i].setup(opt.get("type", PropertyWidget.EXPRESSION), self.layer.mapLayer, opt)

        for i in range(GEOM_WIDGET_MAX_COUNT):
            self.geomWidgets[i].setVisible(bool(i < len(geomItems)))

        # material
        self.comboEdit_Color.setVisible(color)

        self.comboEdit_Color2.setVisible(bool(color2))
        if color2:
            self.comboEdit_Color2.setup(PropertyWidget.OPTIONAL_COLOR, self.layer.mapLayer, color2)

        self.comboEdit_Opacity.setVisible(opacity)

        mtlItems = mtlItems or []
        for i, opt in enumerate(mtlItems):
            self.mtlWidgets[i].setup(opt.get("type", PropertyWidget.EXPRESSION), self.layer.mapLayer, opt)

        for i in range(MTL_WIDGET_MAX_COUNT):
            self.mtlWidgets[i].setVisible(bool(i < len(mtlItems)))

        self.groupBox_Material.setVisible(bool(color or color2 or opacity or mtlItems))

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

    def labelToggled(self, checked):
        for grp in [self.groupBox_Position, self.groupBox_LabelText, self.groupBox_Background, self.groupBox_Conn]:
            grp.setEnabled(checked)


class PointCloudPropertyPage(PropertyPage, Ui_PCPropertiesWidget):

    def __init__(self, parent, layer):
        PropertyPage.__init__(self, parent, PAGE_POINTCLOUD)
        Ui_PCPropertiesWidget.setupUi(self, self)

        widgets = [
            self.lineEdit_Name, self.url, self.comboBox_ColorType, self.colorButton_Color, self.spinBox_Opacity,
            self.checkBox_BoxVisible, self.checkBox_Visible, self.checkBox_Clickable
        ]
        self.registerPropertyWidgets(widgets)

        if layer.mapLayer:
            self.lineEdit_Name.setPlaceholderText(layer.mapLayer.name())
        else:
            self.lineEdit_Name.setText(layer.name)
            self.lineEdit_Name.setPlaceholderText(layer.name)

        color_types = ["RGB", "COLOR", "HEIGHT", "INTENSITY", "INTENSITY_GRADIENT", "POINT_INDEX", "CLASSIFICATION", "RETURN_NUMBER"]
        # ["RGB", "COLOR", "DEPTH", "HEIGHT", "INTENSITY", "INTENSITY_GRADIENT", "LOD", "POINT_INDEX",
        #  "CLASSIFICATION", "RETURN_NUMBER", "SOURCE", "NORMAL", "PHONG", "RGB_HEIGHT", "COMPOSITE"]

        for t in color_types:
            self.comboBox_ColorType.addItem(t, t)

        self.comboBox_ColorType.currentIndexChanged.connect(self.colorTypeChanged)
        self.colorTypeChanged()

        self.restoreProperties(layer.properties)

        total_points = loaded_points = visible_points = bbox = None

        url = layer.properties.get("url", "")
        if url.startswith("file:") and url.endswith(("cloud.js", "ept.json")):
            try:
                with open(QUrl(url).toLocalFile(), "r") as f:
                    d = json.load(f)

                total_points = d.get("points")
                bbox = d.get("tightBoundingBox")        # potree
                if bbox:
                    bbox = [bbox.get("lx"), bbox.get("ly"), bbox.get("lz"), bbox.get("ux"), bbox.get("uy"), bbox.get("uz")]
                else:
                    bbox = d.get("boundsConforming")    # ept
            except:
                pass

        def updateInfoBox():
            html = "<style>th {text-align:left;padding-right:10px;}</style><table>"
            for name, count in [("Point", total_points), ("Loaded point", loaded_points), ("Visible point", visible_points)]:
                fmtCount = "Unknown" if count is None else "{:,}".format(int(count))
                html += f"<tr><th>{name} count</th><td>{fmtCount}</td></tr>"

            if bbox:
                html += """
    <tr><th>Bounding box:</th><td>{:.3f}, {:.3f}, {:.3f} :<br>{:.3f}, {:.3f}, {:.3f}</td></tr>
    """.format(*bbox)

            html += "</table>"
            self.textBrowser.setHtml(html)

        def updateStat(name, value):
            nonlocal loaded_points, visible_points

            if name == "loaded":
                loaded_points = value
            elif name == "visible":
                visible_points = value

            updateInfoBox()

        updateInfoBox()

        wnd = self.parent().parent()
        layer_js = f"app.scene.mapLayers[{layer.jsLayerId}]"
        wnd.runScript(f"{layer_js}.loadedPointCount()", callback=lambda v: updateStat("loaded", v))
        wnd.runScript(f"{layer_js}.pcg.children[0].numVisiblePoints", callback=lambda v: updateStat("visible", v))

    def colorTypeChanged(self, index=None):
        b = (self.comboBox_ColorType.currentData() == "COLOR")
        self.label_Color.setEnabled(b)
        self.colorButton_Color.setEnabled(b)
