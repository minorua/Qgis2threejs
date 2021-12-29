# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ExportSettings
                              -------------------
        begin                : 2014-01-16
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
from copy import deepcopy

from PyQt5.QtCore import QSettings, QSize
from qgis.core import QgsMapSettings, QgsPointXY, QgsProject

from . import q3dconst
from .conf import DEF_SETS, DEBUG_MODE, PLUGIN_VERSION_INT
from .pluginmanager import pluginManager
from .mapextent import MapExtent
from .q3dcore import MapTo3D, Layer, GDALDEMProvider, FlatDEMProvider, calculateGridSegments
from .tools import getLayersInProject, getTemplateConfig, logMessage, settingsFilePath


class ExportSettings:

    SCENE = "SCENE"
    CAMERA = "CAMERA"
    CONTROLS = "CTRL"
    LAYERS = "LAYERS"
    WIDGETS = "WIDGETS"
    KEYFRAMES = "KEYFRAMES"
    OPTIONS = "OPT"   # web export options
    DECOR = "DECOR"   # obsolete since version 2.6

    WIDGET_LIST = ["Navi", "NorthArrow", "Label"]

    def __init__(self):
        self.data = {}
        self.mapSettings = None
        self.crs = None

        self.base64 = False
        self.isPreview = False
        self.localMode = False

        self.nextJsLayerId = 0

        # cache
        self._baseExtent = None
        self._mapTo3d = None
        self._templateConfig = None

    def clear(self):
        self.data = {}

    def clone(self):
        s = ExportSettings()
        self.copyTo(s)
        return s

    def copyTo(self, t):
        t.data = deepcopy(self.data)
        t.mapSettings = QgsMapSettings(self.mapSettings) if self.mapSettings else None
        t.crs = self.crs
        t.base64 = self.base64
        t.isPreview = self.isPreview
        t.localMode = self.localMode
        t.nextJsLayerId = self.nextJsLayerId

    def get(self, key, default=None):
        return self.data.get(key, default)

    def loadSettings(self, settings):
        self.data = settings
        self._baseExtent = None
        self._mapTo3d = None
        self.updateLayerList()

    def loadSettingsFromFile(self, filepath=None):
        """load settings from a JSON file"""
        self.data = {}
        if filepath is None:
            filepath = settingsFilePath()   # get settings file path for current project
            if filepath is None:
                self.updateLayerList()
                return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception as e:
            logMessage("Failed to load export settings from file. Error: " + str(e))
            self.updateLayerList()
            return False

        logMessage("Export settings loaded from file:" + filepath, False)

        # transform layer dict to Layer object
        settings[ExportSettings.LAYERS] = [Layer.fromDict(lyr) for lyr in settings.get(ExportSettings.LAYERS, [])]

        if settings.get("Version", 0) < 270:
            try:
                self.loadEarlierFormatData(settings)
            except Exception as e:
                logMessage("ExportSettings: Failed to load some properties which were saved in an earlier plugin version.")

                if DEBUG_MODE:
                    raise e
        else:
            self.loadSettings(settings)
        return True

    def saveSettings(self, filepath=None):
        """save settings to a JSON file"""
        if filepath is None:
            filepath = settingsFilePath()
            if filepath is None:
                return False

        self.data["Version"] = PLUGIN_VERSION_INT

        def default(obj):
            if isinstance(obj, Layer):
                return obj.toDict()
            raise TypeError(repr(obj) + " is not JSON serializable")

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2, default=default, sort_keys=True)
            return True
        except Exception as e:
            logMessage("Failed to save export settings: " + str(e))
            return False

    def setMapSettings(self, settings):
        """settings: QgsMapSettings"""
        self._baseExtent = None
        self._mapTo3d = None
        self.mapSettings = settings

        self.setCrs(settings.destinationCrs())

    def setCrs(self, crs):
        self.crs = crs

    def baseExtent(self):
        if self._baseExtent:
            return self._baseExtent

        sp = self.sceneProperties()
        if sp.get("radioButton_FixedExtent", False):
            try:
                self._baseExtent = MapExtent(QgsPointXY(float(sp.get("lineEdit_CenterX", 0)),
                                                        float(sp.get("lineEdit_CenterY", 0))),
                                             float(sp.get("lineEdit_Width", 0)),
                                             float(sp.get("lineEdit_Height", 0)),
                                             float(sp.get("lineEdit_Rotation", 0)))
            except ValueError:
                logMessage("Invalid extent. Check out scene properties.")

        elif self.mapSettings:
            self._baseExtent = MapExtent.fromMapSettings(self.mapSettings, sp.get("checkBox_FixAspectRatio", False))

        return self._baseExtent

    def mapTo3d(self):
        if self._mapTo3d:
            return self._mapTo3d

        be = self.baseExtent()
        if be is None:
            return None

        sp = self.sceneProperties()
        try:
            baseSize = float(sp.get("lineEdit_BaseSize", DEF_SETS.BASE_SIZE))
            zExaggeration = float(sp.get("lineEdit_zFactor", DEF_SETS.Z_EXAGGERATION))
            zShift = float(sp.get("lineEdit_zShift", DEF_SETS.Z_SHIFT))

            self._mapTo3d = MapTo3D(be, baseSize, zExaggeration, zShift)

        except ValueError:
            self._mapTo3d = MapTo3D(be, DEF_SETS.BASE_SIZE, DEF_SETS.Z_EXAGGERATION, DEF_SETS.Z_SHIFT)

            logMessage("Invalid setting values. Check out scene properties.")

        return self._mapTo3d

    def checkValidity(self):
        """check validity of export settings. return error message as str. return None if valid."""
        return None

    # web export
    def template(self):
        return self.data.get("Template", DEF_SETS.TEMPLATE)

    def setTemplate(self, filepath):
        """filepath: relative path from html_templates directory or absolute path to a template html file"""
        self.data["Template"] = filepath
        self._templateConfig = None

    def templateConfig(self):
        if self._templateConfig:
            return self._templateConfig
        self._templateConfig = getTemplateConfig(self.template())
        return self._templateConfig

    def outputFileName(self):
        return self.data.get("OutputFilename", "")

    def outputFileTitle(self):
        return os.path.splitext(os.path.basename(self.outputFileName()))[0]

    def outputDirectory(self):
        return os.path.split(self.outputFileName())[0]

    def outputDataDirectory(self):
        return os.path.join(self.outputDirectory(), "data", self.outputFileTitle())

    def setOutputFilename(self, filepath=""):
        self.data["OutputFilename"] = filepath

    def title(self):
        return self.data.get("Title", "")

    def setTitle(self, title):
        self.data["Title"] = title

    def options(self):
        return self.data.get(ExportSettings.OPTIONS, {})

    def option(self, key):
        return self.data.get(ExportSettings.OPTIONS, {}).get(key)

    def setOption(self, key, value):
        self.data[ExportSettings.OPTIONS] = self.data.get(ExportSettings.OPTIONS, {})
        self.data[ExportSettings.OPTIONS][key] = value

    def clearOptions(self):
        self.data[ExportSettings.OPTIONS] = {}

    # scene
    def sceneProperties(self):
        return self.data.get(ExportSettings.SCENE, {})

    def setSceneProperties(self, properties):
        self.data[ExportSettings.SCENE] = properties
        self._baseExtent = None
        self._mapTo3d = None

    def materialType(self):
        return self.sceneProperties().get("comboBox_MaterialType", 0)

    def useOutlineEffect(self):
        return self.sceneProperties().get("checkBox_Outline", False)

    def coordDisplay(self):
        return not self.sceneProperties().get("radioButton_NoCoords", False)

    def coordLatLon(self):
        return self.sceneProperties().get("radioButton_WGS84", False)

    def needsProjString(self):
        return self.coordLatLon() or (not self.isPreview and "proj4.js" in self.templateConfig().get("scripts", ""))

    # camera
    def isOrthoCamera(self):
        return (self.data.get(ExportSettings.CAMERA) == "ORTHO")

    def setCamera(self, is_ortho):
        self.data[ExportSettings.CAMERA] = "ORTHO" if is_ortho else "PERSPECTIVE"

    # controls
    def controls(self):
        ctrl = self.data.get(ExportSettings.CONTROLS, {}).get("comboBox_Controls")
        if ctrl:
            return ctrl
        return QSettings().value("/Qgis2threejs/lastControls", DEF_SETS.CONTROLS, type=str)

    def setControls(self, name):
        self.data[ExportSettings.CONTROLS] = {"comboBox_Controls": name}

    # layer
    def getLayerList(self):
        return self.data.get(ExportSettings.LAYERS, [])

    def layersToExport(self):
        return [lyr for lyr in self.getLayerList() if lyr.visible]

    def mapLayerIdsToExport(self):
        return [lyr.layerId for lyr in self.getLayerList() if lyr.visible]

    def jsLayerIdsToExport(self):
        return [lyr.jsLayerId for lyr in self.getLayerList() if lyr.visible]

    def updateLayerList(self):
        """Updates layer elements in settings using current project layer structure.
           Adds layer elements newly added to the project and removes layer elements
           deleted from the project. Also, renumbers layer ID."""

        # Point cloud layers
        layers = [lyr for lyr in self.getLayerList() if lyr.layerId.startswith("pc:")]

        # DEM and vector layers
        for mapLayer in [ml for ml in getLayersInProject() if Layer.getGeometryType(ml) is not None]:
            item = self.getLayer(mapLayer.id())
            if item:
                # update layer and layer name
                item.mapLayer = mapLayer
                item.name = mapLayer.name()
            else:
                item = Layer.fromQgsMapLayer(mapLayer)
            layers.append(item)

        # DEM provider plugin layers
        for plugin in pluginManager().demProviderPlugins():
            layerId = "plugin:" + plugin.providerId()
            item = self.getLayer(layerId)
            if item is None:
                item = Layer(layerId, plugin.providerName(), q3dconst.TYPE_DEM, visible=False)
            layers.append(item)

        # Flat plane
        layerId = "FLAT"
        item = self.getLayer(layerId)
        if item is None:
            item = Layer(layerId, "Flat Plane", q3dconst.TYPE_DEM, visible=False)
        layers.append(item)

        # renumber jsLayerId
        self.nextJsLayerId = 0
        for layer in layers:
            layer.jsLayerId = self.nextJsLayerId
            self.nextJsLayerId += 1

        self.data[ExportSettings.LAYERS] = layers

    def getLayer(self, layerId):
        if layerId is not None:
            for layer in self.getLayerList():
                if layer.layerId == layerId:
                    return layer
        return None

    def addLayer(self, layer):
        """append an additional layer to layer list"""
        layer = layer.clone()
        layer.jsLayerId = self.nextJsLayerId
        self.nextJsLayerId += 1

        layers = self.getLayerList()
        layers.append(layer)
        self.data[ExportSettings.LAYERS] = layers
        return layer

    def insertLayer(self, index, layer):
        """insert an additional layer to layer list at given index"""
        layer = layer.clone()
        layer.jsLayerId = self.nextJsLayerId
        self.nextJsLayerId += 1

        layers = self.getLayerList()
        layers.insert(index, layer)
        self.data[ExportSettings.LAYERS] = layers
        return layer

    def removeLayer(self, layerId):
        """remove layer with given layer ID from layer list"""
        self.data[ExportSettings.LAYERS] = [lyr for lyr in self.getLayerList() if lyr.layerId != layerId]

    # layer - DEM
    def demProviderByLayerId(self, id):
        if id == "FLAT":
            return FlatDEMProvider()

        if id.startswith("plugin:"):
            provider = pluginManager().findDEMProvider(id[7:])
            if provider:
                return provider(str(self.crs.toWkt()))

            logMessage('Plugin "{0}" not found'.format(id))

        else:
            layer = QgsProject.instance().mapLayer(id)
            if layer:
                return GDALDEMProvider(layer.source(), str(self.crs.toWkt()), source_wkt=str(layer.crs().toWkt()))    # use CRS set to the layer in QGIS

        return FlatDEMProvider()

    def demGridSegments(self, layerId):
        if layerId == "FLAT":
            return QSize(1, 1)

        layer = self.getLayer(layerId)
        if layer:
            return calculateGridSegments(self.baseExtent(),
                                         layer.properties.get("horizontalSlider_DEMSize", 2),
                                         layer.properties.get("spinBox_Roughening", 0) if layer.properties.get("checkBox_Tiles") else 0)
        return QSize(1, 1)

    # widgets
    def widgetProperties(self, name):
        """name: widget name. Navi, NorthArrow or Label."""
        widgets = self.data.get(ExportSettings.WIDGETS, self.data.get(ExportSettings.DECOR, {}))

        if name == "Label":
            p = widgets.get("Label")
            if p:
                return p
            # for backward compatibility
            return {"Header": widgets.get("HeaderLabel", ""),
                    "Footer": widgets.get("FooterLabel", "")}

        return widgets.get(name, {})

    def setWidgetProperties(self, name, properties):
        widgets = self.data.get(ExportSettings.WIDGETS, self.data.get(ExportSettings.DECOR, {}))
        widgets[name] = properties
        self.data[ExportSettings.WIDGETS] = widgets

    def isNavigationEnabled(self):
        return self.widgetProperties("Navi").get("enabled", True)

    def setNavigationEnabled(self, enabled):
        self.setWidgetProperties("Navi", {"enabled": enabled})

    def headerLabel(self):
        return self.widgetProperties("Label").get("Header", "")

    def setHeaderLabel(self, text):
        p = self.widgetProperties("Label")
        p["Header"] = str(text)
        self.setWidgetProperties("Label", p)

    def footerLabel(self):
        return self.widgetProperties("Label").get("Footer", "")

    def setFooterLabel(self, text):
        p = self.widgetProperties("Label")
        p["Footer"] = str(text)
        self.setWidgetProperties("Label", p)

    # animation
    def isAnimationEnabled(self):
        return self.data.get(ExportSettings.KEYFRAMES, {}).get("enabled", False)

    def animationData(self, layerId=None, export=False):
        d = self.data.get(ExportSettings.KEYFRAMES, {})
        if not export:
            if layerId:
                return d.get("layers", {}).get(layerId, {})
            return d

        # for export
        if not d.get("enabled"):
            return {}

        groups = []

        # camera motion
        idx = d.get("cmgIndex", -1)
        if idx >= 0:
            groups.append(deepcopyExcept(d["camera"]["groups"][idx], "name"))

        # layer animation
        idsToExport = self.mapLayerIdsToExport()
        for layerId, layer in d.get("layers", {}).items():
            if layerId in idsToExport:
                groups += deepcopyExcept(layer["groups"], "name")

        return {"groups": groups}

    def setAnimationData(self, data):
        d = self.data.get(ExportSettings.KEYFRAMES, {})
        d.update(data)
        self.data[ExportSettings.KEYFRAMES] = d

    # for backward compatibility
    def loadEarlierFormatData(self, settings):
        for layer in settings[ExportSettings.LAYERS]:
            geomType = layer.geomType
            p = layer.properties

            if geomType in (q3dconst.TYPE_POINT, q3dconst.TYPE_LINESTRING, q3dconst.TYPE_POLYGON):
                objType = p.get("comboBox_ObjectType")

                # two object types were renamed in 2.4
                if objType == "Profile":
                    p["comboBox_ObjectType"] = "Wall"
                elif objType == "Triangular Mesh":
                    p["comboBox_ObjectType"] = "Polygon"

                # styleWidgetX were obsoleted since 2.7
                if objType == "Icon":
                    v = p.get("styleWidget0")
                    if v:
                        p["comboEdit_Opacity"] = v

                    v = p.get("styleWidget1")
                    if v:
                        p["comboEdit_FilePath"] = v

                    self._style2geom(p, 2, 1)

                elif objType == "Model File":
                    v = p.get("styleWidget0")
                    if v:
                        p["expression_FilePath"] = v

                    self._style2geom(p, 1, 5)

                else:
                    # color and opacity
                    v = p.get("styleWidget0")
                    if v:
                        p["comboEdit_Color"] = v

                    v = p.get("styleWidget1")
                    if v:
                        p["comboEdit_Opacity"] = v

                    # other widgets
                    if geomType == q3dconst.TYPE_POINT:
                        if objType == "Point":
                            v = p.get("styleWidget2")
                            if v:
                                p["mtlWidget0"] = v        # size

                        else:
                            self._style2geom(p, 2, 4)

                    elif geomType == q3dconst.TYPE_LINESTRING:
                        if objType == "Line":
                            v = p.get("styleWidget2")
                            if v:
                                p["mtlWidget0"] = v    # dashed

                        elif objType == "Wall":
                            v = p.get("styleWidget2")
                            if v:
                                p["comboEdit_altitude2"] = v

                        else:
                            self._style2geom(p, 2, 2)

                    elif geomType == q3dconst.TYPE_POLYGON:
                        if objType == "Extruded":
                            self._style2geom(p, 2, 1)

                            v = p.get("styleWidget3")
                            if v:
                                p["comboEdit_Color2"] = v

                        elif objType == "Overlay":
                            v = p.get("styleWidget2")
                            if v:
                                p["comboEdit_Color2"] = v

            elif geomType == q3dconst.TYPE_DEM:
                v = p.get("checkBox_Surroundings")      # renamed in 2.7
                if v:
                    p["checkBox_Tiles"] = v

        self.loadSettings(settings)

    def _style2geom(self, properties, offset=0, count=q3dconst.GEOM_WIDGET_MAX_COUNT):
        for i in range(count):
            v = properties.get("styleWidget" + str(i + offset))
            if v:
                properties["geomWidget" + str(i)] = v


def deepcopyExcept(obj, key_to_remove):
    if isinstance(obj, dict):
        return {k: deepcopyExcept(v, key_to_remove) if isinstance(v, (dict, list)) else v for k, v in obj.items() if k != key_to_remove}
    elif isinstance(obj, list):
        return [deepcopyExcept(v, key_to_remove) if isinstance(v, (dict, list)) else v for v in obj]
    return obj
