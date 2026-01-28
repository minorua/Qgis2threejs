# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

from copy import deepcopy
import json
import os
import re

from qgis.PyQt.QtCore import QSettings, QSize, QUrl
from qgis.core import QgsMapSettings, QgsPoint, QgsPointXY, QgsProject

from .const import ATConst, GEOM_WIDGET_MAX_COUNT, LayerType, layerTypeFromMapLayer
from .mapextent import MapExtent
from .mapto3d import MapTo3D
from .build.dem.demprovider import GDALDEMProvider, FlatDEMProvider
from .plugin.pluginmanager import pluginManager
from ..conf import DEF_SETS, DEBUG_MODE, PLUGIN_VERSION_INT
from ..utils import createUid, getLayersInProject, getTemplateConfig, logger, parseFloat, settingsFilePath


class BuildOptions:

    def __init__(self):
        self.onlyMaterial = False
        self.allMaterials = False


class Layer:

    def __init__(self, layerId, name, layerType, properties=None, visible=True):
        self.layerId = layerId
        self.name = name
        self.type = layerType           # const.LayerType
        self.properties = properties or {}
        self.visible = visible

        # internal use
        self.jsLayerId = None
        self.mapLayer = None
        self.opt = BuildOptions()

    def material(self, mtlId):
        for mtl in self.properties.get("materials", []):
            if mtl.get("id") == mtlId:
                return mtl
        return {}

    def mtlIndex(self, mtlId):
        for i, mtl in enumerate(self.properties.get("materials", [])):
            if mtl.get("id") == mtlId:
                return i
        return None

    def clone(self):
        c = Layer(self.layerId, self.name, self.type, deepcopy(self.properties), self.visible)
        c.jsLayerId = self.jsLayerId
        c.mapLayer = self.mapLayer
        return c

    def copyTo(self, t):
        t.layerId = self.layerId
        t.name = self.name
        t.type = self.type
        t.properties = deepcopy(self.properties)
        t.visible = self.visible

        t.jsLayerId = self.jsLayerId
        t.mapLayer = self.mapLayer

    def toDict(self):
        return {"layerId": self.layerId,
                "name": self.name,
                "geomType": self.type,      # TODO: rename geomType to type (low priority)
                "properties": self.properties,
                "visible": self.visible}

    @classmethod
    def fromDict(cls, obj):
        id = obj["layerId"]
        t = obj["geomType"]

        lyr = Layer(id, obj["name"], t, obj["properties"], obj["visible"])
        lyr.mapLayer = QgsProject.instance().mapLayer(id)

        return lyr

    @classmethod
    def fromQgsMapLayer(cls, mapLayer):
        geomType = layerTypeFromMapLayer(mapLayer)
        lyr = Layer(mapLayer.id(), mapLayer.name(), geomType, visible=False)
        lyr.mapLayer = mapLayer

        if geomType == LayerType.POINTCLOUD:
            lyr.properties["url"] = urlFromPCLayer(mapLayer)

        return lyr

    def __deepcopy__(self, memo):
        return self.clone()


class ExportSettings:

    SCENE = "SCENE"
    CAMERA = "CAMERA"
    CAMERA_POSE = "POSE"
    CONTROLS = "CTRL"
    LAYERS = "LAYERS"
    WIDGETS = "WIDGETS"
    KEYFRAMES = "KEYFRAMES"
    OPTIONS = "OPT"   # web export options
    DECOR = "DECOR"   # obsolete since version 2.6

    WIDGET_LIST = ["Navi", "NorthArrow", "Label"]

    def __init__(self):
        # flag
        self._updated = False   # set to True when data, mapSettings or crs is updated

        self.clear()

    def clear(self):
        self.data = {}
        self.mapSettings = None
        self.crs = None

        self.isPreview = False
        self.requiresJsonSerializable = False
        self.localMode = False

        self.nextJsLayerId = 0

        # cache
        self._baseExtent = None
        self._mapTo3d = None
        self._templateConfig = None

        self._updated = True

    def isUpdated(self):
        return self._updated

    def clearUpdatedFlag(self):
        self._updated = False

    def clone(self):
        s = ExportSettings()
        self.copyTo(s)
        return s

    def copyTo(self, t):
        t.data = deepcopy(self.data)
        t.mapSettings = QgsMapSettings(self.mapSettings) if self.mapSettings else None
        t.crs = self.crs
        t.isPreview = self.isPreview
        t.requiresJsonSerializable = self.requiresJsonSerializable
        t.localMode = self.localMode
        t.nextJsLayerId = self.nextJsLayerId

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self._updated = True

    def initialize(self, mapSettings=None, isPreview=False, requiresJsonSerializable=False):
        self.clear()

        if mapSettings:
            self.setMapSettings(mapSettings)

        self.isPreview = isPreview
        self.requiresJsonSerializable = requiresJsonSerializable

    def loadSettings(self, settings):
        self.data = settings
        self._baseExtent = None
        self._mapTo3d = None
        self._updated = True

        self.updateLayers()

    def loadSettingsFromFile(self, filepath=None):
        """load settings from a JSON file"""
        self.data = {}
        if not filepath:
            filepath = settingsFilePath()   # get settings file path for current project
            if not os.path.exists(filepath):
                self.updateLayers()
                return False

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                settings = json.load(f)
        except Exception as e:
            logger.error("Failed to load export settings from file. Error: " + str(e))
            self.updateLayers()
            return False

        logger.info("Export settings loaded from file:" + filepath)

        # transform layer dict to Layer object
        settings[ExportSettings.LAYERS] = [Layer.fromDict(lyr) for lyr in settings.get(ExportSettings.LAYERS, [])]

        if settings.get("Version", 0) < 20700:
            try:
                self.loadEarlierFormatData(settings)
            except Exception as e:
                logger.warning("ExportSettings: Failed to load some properties which were saved with an earlier plugin version.")

                if DEBUG_MODE:
                    raise e
        else:
            self.loadSettings(settings)
        return True

    def saveSettings(self, filepath=None):
        """save settings to a JSON file"""
        if not filepath:
            filepath = settingsFilePath()
            if not filepath:
                return False

        self.set("Version", PLUGIN_VERSION_INT)

        def default(obj):
            if isinstance(obj, Layer):
                return obj.toDict()
            raise TypeError(repr(obj) + " is not JSON serializable")

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2, default=default, sort_keys=True)
            return True
        except Exception as e:
            logger.warning("Failed to save export settings: " + str(e))
            return False

    def setMapSettings(self, settings):
        """settings: QgsMapSettings"""
        self.mapSettings = settings
        self._baseExtent = None
        self._mapTo3d = None
        self._updated = True

        self.setCrs(settings.destinationCrs())

    def setCrs(self, crs):
        self.crs = crs
        self._updated = True

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
                logger.warning("Invalid extent. Check out scene properties.")

        elif self.mapSettings:
            self._baseExtent = MapExtent.fromMapSettings(self.mapSettings, sp.get("checkBox_FixAspectRatio", True))

        return self._baseExtent

    def mapTo3d(self):
        if self._mapTo3d:
            return self._mapTo3d

        be = self.baseExtent()
        if be is None:
            return None

        sp = self.sceneProperties()
        try:
            zScale = float(sp.get("lineEdit_zFactor", DEF_SETS.Z_EXAGGERATION))
            zShift = DEF_SETS.Z_SHIFT

        except ValueError:
            zScale = DEF_SETS.Z_EXAGGERATION
            zShift = DEF_SETS.Z_SHIFT
            logger.warning("Invalid z exaggeration. Check out scene properties.")

        if sp.get("comboBox_xyShift", True):
            origin = QgsPoint(be.center().x(), be.center().y(), -zShift)
        else:
            origin = QgsPoint(0, 0, -zShift)

        self._mapTo3d = MapTo3D(be, origin, zScale)

        return self._mapTo3d

    def checkValidity(self):
        """check validity of export settings. return error message as str. return None if valid."""
        return None

    # web export
    def template(self):
        return self.data.get("Template", DEF_SETS.TEMPLATE)

    def setTemplate(self, filepath):
        """filepath: relative path from html_templates directory or absolute path to a template html file"""
        self.set("Template", filepath)
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
        self.set("OutputFilename", filepath)

    def title(self):
        return self.data.get("Title", "")

    def setTitle(self, title):
        self.set("Title", title)

    def options(self):
        return self.data.get(ExportSettings.OPTIONS, {})

    def option(self, key):
        return self.data.get(ExportSettings.OPTIONS, {}).get(key)

    def setOption(self, key, value):
        d = self.data.get(ExportSettings.OPTIONS, {})
        d[key] = value
        self.set(ExportSettings.OPTIONS, d)

    def clearOptions(self):
        self.set(ExportSettings.OPTIONS, {})

    # scene
    def sceneProperties(self):
        return self.data.get(ExportSettings.SCENE, {})

    def setSceneProperties(self, properties):
        self.set(ExportSettings.SCENE, properties)
        self._baseExtent = None
        self._mapTo3d = None

    def materialType(self):
        return self.sceneProperties().get("comboBox_MaterialType", 0)

    def useOutlineEffect(self):
        return self.sceneProperties().get("checkBox_Outline", False)

    def coordDisplay(self):
        return not self.sceneProperties().get("radioButton_NoCoords", False)

    def isCoordLatLon(self):
        return self.sceneProperties().get("radioButton_WGS84", False)

    def needsProjString(self):
        return self.isCoordLatLon() or (not self.isPreview and "proj4.js" in self.templateConfig().get("scripts", ""))

    # camera
    def isOrthoCamera(self):
        return (self.data.get(ExportSettings.CAMERA) == "ORTHO")

    def setCamera(self, is_ortho):
        self.set(ExportSettings.CAMERA, "ORTHO" if is_ortho else "PERSPECTIVE")

    # camera pose
    def cameraPose(self):
        """return (position, target): QgsPoint"""
        p = self.data.get(ExportSettings.CAMERA_POSE, {})
        pos = p.get("position")
        tgt = p.get("target")
        return (QgsPoint(pos[0], pos[1], pos[2]) if pos else None,
                QgsPoint(tgt[0], tgt[1], tgt[2]) if tgt else None)

    def setCameraPose(self, position, target):
        """position, target: dict with x, y, z keys"""
        p = self.data.get(ExportSettings.CAMERA_POSE, {})
        p["position"] = [position["x"], position["y"], position["z"]]
        p["target"] = [target["x"], target["y"], target["z"]]
        self.set(ExportSettings.CAMERA_POSE, p)

    # controls
    def controls(self):
        ctrl = self.data.get(ExportSettings.CONTROLS, {}).get("comboBox_Controls")
        if ctrl:
            return ctrl
        return QSettings().value("/Qgis2threejs/lastControls", DEF_SETS.CONTROLS, type=str)

    def setControls(self, name):
        self.set(ExportSettings.CONTROLS, {"comboBox_Controls": name})

    # layer
    def layers(self, export_only=False):
        layers = self.data.get(ExportSettings.LAYERS, [])
        if export_only:
            return [lyr for lyr in layers if lyr.visible]

        return layers

    def layerIdsToExport(self):
        return [lyr.layerId for lyr in self.layers(export_only=True)]

    def updateLayers(self):
        """Updates layer objects in settings using current project layer structure.
           Adds layer objects newly added to the project and removes layer objects
           deleted from the project. Layer IDs are renumbered."""

        # Additional point cloud layers
        layers = [lyr for lyr in self.layers() if lyr.layerId.startswith("pc:")]

        # DEM, vector and point cloud layers in QGIS project
        for mapLayer in getLayersInProject():
            layerType = layerTypeFromMapLayer(mapLayer)
            if layerType is None:
                continue

            layer = self.getLayer(mapLayer.id())
            if layer:
                # update layer and layer name
                layer.mapLayer = mapLayer
                layer.name = layer.properties.get("lineEdit_Name") or mapLayer.name()

                if layerType == LayerType.POINTCLOUD:
                    layer.properties["url"] = urlFromPCLayer(mapLayer)     # update url
            else:
                layer = Layer.fromQgsMapLayer(mapLayer)
            layers.append(layer)

        # DEM provider plugin layers
        for plugin in pluginManager().demProviderPlugins():
            layerId = "plugin:" + plugin.providerId()
            layer = self.getLayer(layerId)
            if layer is None:
                layer = Layer(layerId, plugin.providerName(), LayerType.DEM, visible=False)
            layers.append(layer)

        # Flat plane
        layer = self.getLayer("FLAT")        # for backward compatibility. id "FLAT" is obsolete since 2.7
        if layer:
            layer.layerId = "fp:" + createUid()
            layers.append(layer)
        elif len(self.layers()):
            layers += [lyr for lyr in self.layers() if lyr.layerId.startswith("fp:")]
        else:
            layerId = "fp:" + createUid()
            layer = Layer(layerId, "Flat Plane", LayerType.DEM, visible=False)
            layers.append(layer)

        # renumber jsLayerId
        self.nextJsLayerId = 0
        for layer in layers:
            layer.jsLayerId = self.nextJsLayerId
            self.nextJsLayerId += 1

        self.set(ExportSettings.LAYERS, layers)

    def getLayer(self, layerId):
        if layerId:
            for layer in self.layers():
                if layer.layerId == layerId:
                    return layer

    def getLayerByJSLayerId(self, jsLayerId):
        if jsLayerId is None:
            return None

        for layer in self.layers():
            if layer.jsLayerId == jsLayerId:
                return layer

    def setLayer(self, layer):
        """update layer in layer list"""
        target = self.getLayer(layer.layerId)
        if target:
            layer.copyTo(target)
            self._updated = True

    def addLayer(self, layer):
        """append an additional layer to layer list"""
        layer = layer.clone()
        layer.jsLayerId = self.nextJsLayerId
        self.nextJsLayerId += 1

        layers = self.layers()
        layers.append(layer)
        self.set(ExportSettings.LAYERS, layers)
        return layer

    def insertLayer(self, index, layer):
        """insert an additional layer to layer list at given index"""
        layer = layer.clone()
        layer.jsLayerId = self.nextJsLayerId
        self.nextJsLayerId += 1

        layers = self.layers()
        layers.insert(index, layer)
        self.set(ExportSettings.LAYERS, layers)
        return layer

    def removeLayer(self, layerId):
        """remove layer with given layer ID from layer list"""
        self.set(ExportSettings.LAYERS, [lyr for lyr in self.layers() if lyr.layerId != layerId])

    # layer - DEM
    def demProviderByLayerId(self, id):
        if id.startswith("fp:"):
            layer = self.getLayer(id)
            alt = parseFloat(layer.properties.get("lineEdit_Altitude", 0)) if layer else 0
            return FlatDEMProvider(alt or 0)

        if id.startswith("plugin:"):
            provider = pluginManager().findDEMProvider(id[7:])
            if provider:
                return provider(str(self.crs.toWkt()))

            logger.warning('Plugin "{0}" not found'.format(id))

        else:
            layer = QgsProject.instance().mapLayer(id)
            if layer:
                return GDALDEMProvider(layer.source(), str(self.crs.toWkt()), source_wkt=str(layer.crs().toWkt()))    # use CRS set to the layer in QGIS

        return FlatDEMProvider()

    def demGridSegments(self, layerId):
        if layerId.startswith("fp:"):
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
        self.set(ExportSettings.WIDGETS, widgets)

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

    def enabledValidKeyframeGroups(self, layerId=None, warning_log=None):
        if warning_log is None:
            warning_log = logger.warning

        def warn_one_keyframe(group):
            warning_log("'{}' group has only one keyframe. At least two keyframes are necessary for this group to work.".format(group["name"]))

        d = self.data.get(ExportSettings.KEYFRAMES, {})

        if layerId is None:
            # camera motion
            count = 0
            for group in d.get("camera", {}).get("groups", []):
                if group["enabled"]:
                    if len(group["keyframes"]) > 1:
                        count += 1
                        yield group
                    else:
                        warn_one_keyframe(group)

            if count > 1:
                warning_log("There are {} enabled camera motion groups. They may not work properly due to conflicts.".format(count))

        # layer animation
        layers = d.get("layers", {})
        idsToExport = self.layerIdsToExport()

        if layerId is not None:
            layer = layers.get(layerId)
            if layer:
                layers = {layerId: layer}
            else:
                return

        for layerId, layer in layers.items():
            if layerId not in idsToExport:
                continue

            for group in layer["groups"]:
                if not group["enabled"]:
                    continue

                if group["type"] == ATConst.ITEM_GRP_GROWING_LINE:
                    layer = self.getLayer(layerId)
                    if layer:
                        if layer.properties.get("comboBox_ObjectType") in ["Line", "Thick Line"]:
                            yield group
                        else:
                            warning_log("Layer '{}': Growing line animation is available with 'Line' and 'Thick Line'.".format(layer.name))
                    else:
                        warning_log("Layer not found: {}".format(layerId))

                elif len(group["keyframes"]) > 1:
                    yield group

                else:
                    warn_one_keyframe(group)

    def hasEnabledValidKeyframeGroup(self):
        for _ in self.enabledValidKeyframeGroups():
            return True

        return False

    def animationData(self, layerId=None, export=False, warning_log=None):
        d = self.data.get(ExportSettings.KEYFRAMES, {})
        if not export:
            if layerId:
                return d.get("layers", {}).get(layerId, {})
            return d

        # for export
        if not d.get("enabled"):
            return {}

        return {
            "groups": deepcopyExcept(list(self.enabledValidKeyframeGroups(warning_log=warning_log)), ["name", "text"])
        }

    def setAnimationData(self, data):
        d = self.data.get(ExportSettings.KEYFRAMES, {})
        d.update(data)
        self.set(ExportSettings.KEYFRAMES, d)

    def groupsWithExpressions(self, layerId=None):
        for group in self.enabledValidKeyframeGroups(layerId=layerId):
            if group.get("type") == ATConst.ITEM_GRP_GROWING_LINE:
                for k in group.get("keyframes", []):
                    if k.get("sequential"):
                        yield group
                        break

    def narrations(self, indent=2, indent_width=2, warning_log=None):
        s = " " * indent_width
        pattern = re.compile("<img.+?src=[\"|\'](.+?)[\"|\'].*?>", re.IGNORECASE)
        img_dir = "./data/{}/img/".format(self.outputFileTitle())

        d = []
        files = set()
        for g in self.enabledValidKeyframeGroups(warning_log=warning_log):
            for k in g.get("keyframes", []):
                nar = k.get("narration")
                if not nar:
                    continue

                content = nar["text"]
                for url in pattern.findall(content):
                    if url.startswith("file://"):
                        u = QUrl(url)
                        content = content.replace(url, img_dir + u.fileName())
                        files.add(u.toLocalFile())

                content = "\n".join(map(lambda r: s * (indent + 1) + r, content.split("\n")))
                html = '{}<div id="{}" class="narcontent">\n{}\n{}</div>'.format(s * indent, nar["id"], content, s * indent)
                d.append(html)

        return {
            "html": "\n".join(d),
            "files": list(files)
        }

    # for backward compatibility with < 2.7
    def loadEarlierFormatData(self, settings):
        for layer in settings[ExportSettings.LAYERS]:
            p = layer.properties

            if layer.type in (LayerType.POINT, LayerType.LINESTRING, LayerType.POLYGON):
                objType = p.get("comboBox_ObjectType")

                # renamed in 2.4
                if objType == "Profile":
                    p["comboBox_ObjectType"] = "Wall"
                elif objType == "Triangular Mesh":
                    p["comboBox_ObjectType"] = "Polygon"

                # styleWidgetX were obsoleted since 2.7
                if objType == "Icon":
                    p["comboBox_ObjectType"] = "Billboard"      # renamed in 2.7
                    v = p.get("styleWidget0")
                    if v:
                        p["comboEdit_Opacity"] = v

                    v = p.get("styleWidget1")
                    if v:
                        p["comboEdit_FilePath"] = v

                    self._style2geom(p, 2, 1)

                elif objType == "Model File":
                    p["comboBox_ObjectType"] = "3D Model"      # renamed in 2.7
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
                    if layer.type == LayerType.POINT:
                        if objType == "Point":
                            v = p.get("styleWidget2")
                            if v:
                                p["mtlWidget0"] = v        # size

                        else:
                            self._style2geom(p, 2, 4)

                    elif layer.type == LayerType.LINESTRING:
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

                    elif layer.type == LayerType.POLYGON:
                        if objType == "Extruded":
                            self._style2geom(p, 2, 1)

                            v = p.get("styleWidget3")
                            if v:
                                p["comboEdit_Color2"] = v

                        elif objType == "Overlay":
                            v = p.get("styleWidget2")
                            if v:
                                p["comboEdit_Color2"] = v

            elif layer.type == LayerType.DEM:
                v = p.get("checkBox_Surroundings")      # renamed in 2.7
                if v:
                    p["checkBox_Tiles"] = v

        self.loadSettings(settings)

    def _style2geom(self, properties, offset=0, count=GEOM_WIDGET_MAX_COUNT):
        for i in range(count):
            v = properties.get("styleWidget" + str(i + offset))
            if v:
                properties["geomWidget" + str(i)] = v


def calculateGridSegments(extent, sizeLevel, roughness=0):
    width, height = extent.width(), extent.height()
    size = 100 * sizeLevel
    s = (size * size / (width * height)) ** 0.5
    width = round(width * s)
    height = round(height * s)

    if roughness:
        if width % roughness != 0:
            width = int(width / roughness + 0.9999) * roughness
        if height % roughness != 0:
            height = int(height / roughness + 0.9999) * roughness

    return QSize(width, height)


def deepcopyExcept(obj, keys_to_remove):
    if isinstance(obj, dict):
        return {k: deepcopyExcept(v, keys_to_remove) if isinstance(v, (dict, list)) else v for k, v in obj.items() if k not in keys_to_remove}
    elif isinstance(obj, list):
        return [deepcopyExcept(v, keys_to_remove) if isinstance(v, (dict, list)) else v for v in obj]
    return obj


def urlFromPCLayer(mapLayer):
    src = mapLayer.source()
    if src.startswith("http"):
        return ""       # not supported yet

    if mapLayer.providerType() == "ept":
        f = src
    else:       # assume provider type is pdal
        f = os.path.join(os.path.split(src)[0],
                         "ept_" + os.path.splitext(os.path.basename(src))[0],
                         "ept.json")

    return QUrl.fromLocalFile(f).toString()
