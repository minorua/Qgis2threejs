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
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMapLayer, QgsMapSettings, QgsProject, QgsWkbTypes

from . import q3dconst
from .conf import DEF_SETS
from .pluginmanager import pluginManager
from .mapextent import MapExtent
from .qgis2threejscore import MapTo3D, GDALDEMProvider, FlatDEMProvider, calculateDEMSize
from .qgis2threejstools import getLayersInProject, getTemplateConfig, logMessage, settingsFilePath


class Layer:

    def __init__(self, layerId, name, geomType, properties=None, visible=False):
        self.layerId = layerId
        self.name = name
        self.geomType = geomType        # q3dconst.TYPE_XXX
        self.properties = properties or {}
        self.visible = visible

        self.jsLayerId = None
        self.mapLayer = None
        self.updated = False

    def clone(self):
        c = Layer(self.layerId, self.name, self.geomType, deepcopy(self.properties), self.visible)
        c.jsLayerId = self.jsLayerId
        c.mapLayer = self.mapLayer
        c.updated = self.updated
        return c

    def copyTo(self, t):
        t.layerId = self.layerId
        t.name = self.name
        t.geomType = self.geomType
        t.properties = deepcopy(self.properties)
        t.visible = self.visible

        t.jsLayerId = self.jsLayerId
        t.mapLayer = self.mapLayer
        t.updated = self.updated

    def toDict(self):
        return {"layerId": self.layerId,
                "name": self.name,
                "geomType": self.geomType,
                "properties": self.properties,
                "visible": self.visible}

    @classmethod
    def fromDict(self, obj):
        id = obj["layerId"]
        lyr = Layer(id, obj["name"], obj["geomType"], obj["properties"], obj["visible"])
        lyr.mapLayer = QgsProject.instance().mapLayer(id)
        return lyr

    @classmethod
    def fromQgsMapLayer(cls, layer):
        lyr = Layer(layer.id(), layer.name(), cls.getGeometryType(layer))
        lyr.mapLayer = layer
        return lyr

    @classmethod
    def getGeometryType(cls, layer):
        """layer: QgsMapLayer sub-class object"""
        layerType = layer.type()
        if layerType == QgsMapLayer.VectorLayer:
            return {QgsWkbTypes.PointGeometry: q3dconst.TYPE_POINT,
                    QgsWkbTypes.LineGeometry: q3dconst.TYPE_LINESTRING,
                    QgsWkbTypes.PolygonGeometry: q3dconst.TYPE_POLYGON}.get(layer.geometryType())

        elif layerType == QgsMapLayer.RasterLayer and layer.providerType() == "gdal" and layer.bandCount() == 1:
            return q3dconst.TYPE_DEM

        return None

    def __deepcopy__(self, memo):
        return self.clone()


class ExportSettings:

    SCENE = "SCENE"
    CAMERA = "CAMERA"
    CONTROLS = "CTRL"
    LAYERS = "LAYERS"
    DECOR = "DECOR"
    OPTIONS = "OPT"   # web export options

    DECOR_LIST = ["NorthArrow", "Label"]

    def __init__(self):
        self.data = {}
        self.mapSettings = None
        self.baseExtent = None
        self.crs = None
        self.base64 = False
        self.localMode = False

        # cache
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
        t.mapSettings = QgsMapSettings(self.mapSettings)
        t.baseExtent = self.baseExtent.clone()
        t.crs = self.crs
        t.base64 = self.base64

    def sceneProperties(self):
        return self.data.get(ExportSettings.SCENE, {})

    def setSceneProperties(self, properties):
        self.data[ExportSettings.SCENE] = properties
        self._mapTo3d = None

    def coordsInWGS84(self):
        return self.sceneProperties().get("radioButton_WGS84", False)

    def materialType(self):
        return self.sceneProperties().get("comboBox_MaterialType", 0)

    def isOrthoCamera(self):
        return (self.data.get(ExportSettings.CAMERA) == "ORTHO")

    def setCamera(self, is_ortho):
        self.data[ExportSettings.CAMERA] = "ORTHO" if is_ortho else "PERSPECTIVE"

    def controls(self):
        ctrl = self.data.get(ExportSettings.CONTROLS, {}).get("comboBox_Controls")
        if ctrl:
            return ctrl
        return QSettings().value("/Qgis2threejs/lastControls", DEF_SETS.CONTROLS, type=str)

    def setControls(self, name):
        self.data[ExportSettings.CONTROLS] = {"comboBox_Controls": name}

    def loadSettings(self, settings):
        self.data = settings
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

        self.loadSettings(settings)
        return True

    def saveSettings(self, filepath=None):
        """save settings to a JSON file"""
        if filepath is None:
            filepath = settingsFilePath()
            if filepath is None:
                return False

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

    def template(self):
        return self.data.get("Template", DEF_SETS.TEMPLATE)

    def setTemplate(self, filepath):
        """filepath: relative path from html_templates directory or absolute path to a template html file"""
        self.data["Template"] = filepath
        self._templateConfig = None

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

    def options(self):
        return self.data.get(ExportSettings.OPTIONS, {})

    def option(self, key):
        return self.data.get(ExportSettings.OPTIONS, {}).get(key)

    def setOption(self, key, value):
        self.data[ExportSettings.OPTIONS] = self.data.get(ExportSettings.OPTIONS, {})
        self.data[ExportSettings.OPTIONS][key] = value

    def clearOptions(self):
        self.data[ExportSettings.OPTIONS] = {}

    def setMapSettings(self, settings):
        """settings: QgsMapSettings"""
        self._mapTo3d = None
        self.mapSettings = settings

        self.baseExtent = MapExtent.fromMapSettings(settings)
        self.crs = settings.destinationCrs()

    def mapTo3d(self):
        if self._mapTo3d:
            return self._mapTo3d

        if self.mapSettings is None:
            return None

        sp = self.sceneProperties()
        baseSize = sp.get("lineEdit_BaseSize", DEF_SETS.BASE_SIZE)
        verticalExaggeration = sp.get("lineEdit_zFactor", DEF_SETS.Z_EXAGGERATION)
        verticalShift = sp.get("lineEdit_zShift", DEF_SETS.Z_SHIFT)
        self._mapTo3d = MapTo3D(self.mapSettings, float(baseSize), float(verticalExaggeration), float(verticalShift))
        return self._mapTo3d

    def templateConfig(self):
        if self._templateConfig:
            return self._templateConfig
        self._templateConfig = getTemplateConfig(self.template())
        return self._templateConfig

    def wgs84Center(self):
        if self.crs and self.baseExtent:
            wgs84 = QgsCoordinateReferenceSystem(4326)
            transform = QgsCoordinateTransform(self.crs, wgs84, QgsProject.instance())
            return transform.transform(self.baseExtent.center())
        return None

    def get(self, key, default=None):
        return self.data.get(key, default)

    def checkValidity(self):
        """check validity of export settings. return error message as unicode. return None if valid."""
        return None

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

    def demGridSize(self, layerId):
        if layerId == "FLAT":
            return QSize(2, 2)

        layer = self.getItemByLayerId(layerId)
        if layer is None:
            return None

        sizeLevel = layer.properties.get("horizontalSlider_DEMSize", 2)
        roughening = layer.properties.get("spinBox_Roughening", 0) if layer.properties.get("checkBox_Surroundings", False) else 0
        return calculateDEMSize(self.mapSettings.outputSize(), sizeLevel, roughening)

    def getLayerList(self):
        return self.data.get(ExportSettings.LAYERS, [])

    def updateLayerList(self):
        """Updates layer elements in settings using current project layer structure.
           Adds layer elements newly added to the project and removes layer elements
           deleted from the project. Also, renumbers layer ID."""
        layers = []

        # DEM and Vector layers
        for layer in getLayersInProject():
            if Layer.getGeometryType(layer) is not None:
                item = self.getItemByLayerId(layer.id())
                if item is None:
                    item = Layer.fromQgsMapLayer(layer)
                else:
                    # update layer and layer name
                    item.mapLayer = layer
                    item.name = layer.name()
                layers.append(item)

        # DEM provider plugins
        for plugin in pluginManager().demProviderPlugins():
            layerId = "plugin:" + plugin.providerId()
            item = self.getItemByLayerId(layerId)
            if item is None:
                item = Layer(layerId, plugin.providerName(), q3dconst.TYPE_DEM)
            layers.append(item)

        # Flat plane
        layerId = "FLAT"
        item = self.getItemByLayerId(layerId)
        if item is None:
            item = Layer(layerId, "Flat Plane", q3dconst.TYPE_DEM)
        layers.append(item)

        # update jsLayerId
        for index, layer in enumerate(layers):
            layer.jsLayerId = index

        self.data[ExportSettings.LAYERS] = layers

    def getItemByLayerId(self, layerId):
        if layerId is not None:
            for layer in self.getLayerList():
                if layer.layerId == layerId:
                    return layer
        return None

    def decorationProperties(self, name):
        decor = self.data.get(ExportSettings.DECOR, {})
        if name == "Label":
            p = decor.get("Label")
            if p:
                return p
            # for backward compatibility
            return {"Header": decor.get("HeaderLabel", ""),
                    "Footer": decor.get("FooterLabel", "")}

        return decor.get(name, {})

    def setDecorationProperties(self, name, properties):
        decor = self.data.get(ExportSettings.DECOR, {})
        decor[name] = properties
        self.data[ExportSettings.DECOR] = decor

    def headerLabel(self):
        return self.decorationProperties("Label").get("Header", "")

    def setHeaderLabel(self, text):
        p = self.decorationProperties("Label")
        p["Header"] = str(text)
        self.setDecorationProperties("Label", p)

    def footerLabel(self):
        return self.decorationProperties("Label").get("Footer", "")

    def setFooterLabel(self, text):
        p = self.decorationProperties("Label")
        p["Footer"] = str(text)
        self.setDecorationProperties("Label", p)
