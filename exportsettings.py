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
import datetime
import json

from PyQt5.QtCore import QSettings
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMapLayer, QgsProject, QgsWkbTypes

from . import q3dconst
from .conf import def_vals
from .rotatedrect import RotatedRect
from .qgis2threejscore import ObjectTreeItem, MapTo3D, GDALDEMProvider, FlatDEMProvider
from .qgis2threejstools import getLayersInProject, getTemplateConfig, logMessage, settingsFilePath, temporaryOutputDir


class Layer:

  def __init__(self, layerId, name, geomType, properties=None, visible=False):
    self.layerId = layerId
    self.name = name
    self.geomType = geomType
    self.properties = properties
    self.visible = visible

    self.id = None
    self.jsLayerId = None
    self.mapLayer = None
    self.updated = False

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


class ExportSettings:

  # export mode
  PLAIN_SIMPLE = 0
  PLAIN_MULTI_RES = 1
  SPHERE = 2

  #TODO: do not take pluginManager.
  # one instance should be held in Qgis2threejs plugin, and should not be held in export settings.
  def __init__(self, pluginManager=None, localBrowsingMode=True):
    """localBrowsingMode: not implemented yet"""
    self.localBrowsingMode = localBrowsingMode
    self.pluginManager = pluginManager
    if self.pluginManager is None:
      from .pluginmanager import PluginManager
      self.pluginManager = PluginManager()

    self.data = {}
    self.timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

    self.templatePath = None

    self.htmlfilename = None
    self.htmlfiletitle = None

    self.canvas = None
    self.mapSettings = None
    self.baseExtent = None
    self.crs = None

    # cache
    self._mapTo3d = None
    self._templateConfig = None

  def clear(self):
    self.data = {}

  def worldProperties(self):
    return self.data.get(ObjectTreeItem.ITEM_WORLD, {})

  def setWorldProperties(self, properties):
    self.data[ObjectTreeItem.ITEM_WORLD] = properties
    self._mapTo3d = None

  def coordsInWGS84(self):
    return self.data.get(ObjectTreeItem.ITEM_WORLD, {}).get("radioButton_WGS84", False)

  def controls(self):
    ctrl = self.data.get(ObjectTreeItem.ITEM_CONTROLS, {}).get("comboBox_Controls")
    if ctrl:
      return ctrl
    return QSettings().value("/Qgis2threejs/lastControls", def_vals.controls, type=str)

  def setControls(self, name):
    self.data[ObjectTreeItem.ITEM_CONTROLS] = {"comboBox_Controls": name}

  def loadSettings(self, settings):
    self.data = settings
    self._mapTo3d = None

    # output html file path
    self.setOutputFilename(settings.get("OutputFilename"))

    # template
    self.setTemplatePath(settings.get("Template", def_vals.template))

  def loadSettingsFromFile(self, filepath=None):
    """load settings from a JSON file"""
    self.data = {}
    if filepath is None:
      filepath = settingsFilePath()   # get settings file path for current project
      if filepath is None:
        return False

    try:
      with open(filepath, encoding="UTF-8") as f:
        settings = json.load(f)
    except Exception as e:
      logMessage("Failed to load export settings from file. Error: " + str(e))
      return False

    logMessage("Export settings loaded from file:" + filepath)

    # transform layer dict to Layer object
    settings["LAYERS"] = [Layer.fromDict(lyr) for lyr in settings.get("LAYERS", [])]

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
      with open(filepath, "w", encoding="UTF-8") as f:
        json.dump(self.data, f, ensure_ascii=False, indent=2, default=default, sort_keys=True)
      return True
    except Exception as e:
      logMessage("Failed to save export settings: " + str(e))
      return False

  def setTemplatePath(self, filepath):
    """filepath: relative path from html_templates directory or absolute path to a template html file"""
    self.templatePath = filepath
    self._templateConfig = None

  def setOutputFilename(self, filepath=None):
    if not filepath:
      filepath = temporaryOutputDir() + "/%s.html" % self.timestamp   # temporary file
    self.htmlfilename = filepath
    self.htmlfiletitle = os.path.splitext(os.path.basename(filepath))[0]

    self.outputdir = os.path.split(filepath)[0]
    self.outputdatadir = os.path.join(self.outputdir, "data", self.htmlfiletitle)

  def setMapCanvas(self, canvas):
    self.setMapSettings(canvas.mapSettings())
    self.canvas = canvas

  def setMapSettings(self, settings):
    """settings: QgsMapSettings"""
    self.canvas = None
    self._mapTo3d = None
    self.mapSettings = settings

    self.baseExtent = RotatedRect.fromMapSettings(settings)
    self.crs = settings.destinationCrs()

  def mapTo3d(self):
    if self._mapTo3d:
      return self._mapTo3d

    if self.mapSettings is None:
      return None

    world = self.data.get(ObjectTreeItem.ITEM_WORLD, {})
    baseSize = world.get("lineEdit_BaseSize", def_vals.baseSize)
    verticalExaggeration = world.get("lineEdit_zFactor", def_vals.zExaggeration)
    verticalShift = world.get("lineEdit_zShift", def_vals.zShift)
    self._mapTo3d = MapTo3D(self.mapSettings, float(baseSize), float(verticalExaggeration), float(verticalShift))
    return self._mapTo3d

  def templateConfig(self):
    if self._templateConfig:
      return self._templateConfig

    if not self.templatePath:
      self.setTemplatePath(def_vals.template)

    self._templateConfig = getTemplateConfig(self.templatePath)
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
      provider = self.pluginManager.findDEMProvider(id[7:])
      if provider:
        return provider(str(self.crs.toWkt()))

      logMessage('Plugin "{0}" not found'.format(id))

    else:
      layer = QgsProject.instance().mapLayer(id)
      if layer:
        return GDALDEMProvider(layer.source(), str(self.crs.toWkt()), source_wkt=str(layer.crs().toWkt()))    # use CRS set to the layer in QGIS

    return FlatDEMProvider()

  def getLayerList(self):
    return self.data.get("LAYERS", [])

  def updateLayerList(self):
    layers = []

    # DEM and Vector layers
    for layer in getLayersInProject():
      if Layer.getGeometryType(layer) is not None:
        item = self.getItemByLayerId(layer.id())
        if item is None:
          item = Layer.fromQgsMapLayer(layer)
        else:
          item.name = layer.name()    # update layer name
        layers.append(item)

    # DEM provider plugins
    for plugin in self.pluginManager.demProviderPlugins():
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

    # update id and jsLayerId
    for index, layer in enumerate(layers):
      layer.id = index
      layer.jsLayerId = index      # "{}_{}".format(itemId, layerId[:8])

    self.data["LAYERS"] = layers

  def getItemByLayerId(self, layerId):
    if layerId is not None:
      for layer in self.data.get("LAYERS", []):
        if layer.layerId == layerId:
          return layer
    return None
