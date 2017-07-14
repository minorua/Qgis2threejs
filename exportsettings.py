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

from PyQt5.QtCore import QSettings
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMapLayer, QgsProject, QgsWkbTypes

from .conf import def_vals
from .rotatedrect import RotatedRect
from .qgis2threejscore import ObjectTreeItem, MapTo3D, GDALDEMProvider, FlatDEMProvider, createQuadTree
from .qgis2threejstools import getLayersInProject, logMessage
from . import qgis2threejstools as tools
from .viewer2 import q3dconst


class ExportSettings:

  # export mode
  PLAIN_SIMPLE = 0
  PLAIN_MULTI_RES = 1
  SPHERE = 2

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

    self.exportMode = ExportSettings.PLAIN_SIMPLE
    self._controls = None
    self.coordsInWGS84 = False

    self.canvas = None
    self.mapSettings = None
    self.baseExtent = None
    self.crs = None

    # cache
    self._mapTo3d = None
    self._quadtree = None
    self._templateConfig = None

  @property
  def controls(self):
    if self._controls:
      return self._controls
    return QSettings().value("/Qgis2threejs/lastControls", def_vals.controls, type=str)

  @controls.setter
  def controls(self, value):
    self._controls = value

  def loadSettings(self, settings):
    self.data = settings
    self._mapTo3d = None

    # output html file path
    self.setOutputFilename(settings.get("OutputFilename"))

    # template
    self.setTemplatePath(settings.get("Template", def_vals.template))

    # world
    world = settings.get(ObjectTreeItem.ITEM_WORLD, {})
    self.coordsInWGS84 = world.get("radioButton_WGS84", False)

    # controls name
    self._controls = settings.get(ObjectTreeItem.ITEM_CONTROLS, {}).get("comboBox_Controls")

    # export mode
    demProperties = settings.get(ObjectTreeItem.ITEM_DEM, {})
    if self.templateConfig().get("type") == "sphere":
      self.exportMode = ExportSettings.SPHERE
    elif demProperties.get("radioButton_Advanced", False):
      self.exportMode = ExportSettings.PLAIN_MULTI_RES
    else:
      self.exportMode = ExportSettings.PLAIN_SIMPLE

  def loadSettingsFromFile(self, filepath):
    """load settings from JSON file"""
    import json
    with open(filepath) as f:
      settings = json.load(f)
    self.loadSettings(settings)

  def setTemplatePath(self, filepath):
    """filepath: relative path from html_templates directory or absolute path to a template html file"""
    self.templatePath = filepath
    self._templateConfig = None

  def setOutputFilename(self, filepath=None):
    if not filepath:
      filepath = tools.temporaryOutputDir() + "/%s.html" % self.timestamp   # temporary file
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

  def quadtree(self):
    if self._quadtree:
      self._quadtree

    if self.baseExtent is None:
      return

    properties = self.data.get(ObjectTreeItem.ITEM_DEM, {})
    self._quadtree = createQuadTree(self.baseExtent, properties)
    return self._quadtree

  def templateConfig(self):
    if self._templateConfig:
      return self._templateConfig

    if not self.templatePath:
      self.setTemplatePath(def_vals.template)

    self._templateConfig = tools.getTemplateConfig(self.templatePath)
    return self._templateConfig

  def wgs84Center(self):
    if self.crs and self.baseExtent:
      wgs84 = QgsCoordinateReferenceSystem(4326)
      transform = QgsCoordinateTransform(self.crs, wgs84)
      return transform.transform(self.baseExtent.center())
    return None

  def get(self, key, default=None):
    return self.data.get(key, default)

  def checkValidity(self):
    """check validity of export settings. return error message as unicode. return None if valid."""
    if self.exportMode == ExportSettings.PLAIN_MULTI_RES and self.quadtree() is None:
      return "Focus point/area is not selected."
    return None

  def demProviderByLayerId(self, id):
    if id == "FLAT":
      return FlatDEMProvider()

    if id.startswith("plugin:"):
      provider = self.pluginManager.findDEMProvider(id[7:])
      if provider:
        return provider(str(self.crs.toWkt()))

      logMessage('Plugin "{0}" not found'.format(id))
      return FlatDEMProvider()

    else:
      layer = QgsProject.instance().mapLayer(id)
      return GDALDEMProvider(layer.source(), str(self.crs.toWkt()), source_wkt=str(layer.crs().toWkt()))    # use CRS set to the layer in QGIS

  def getLayerList(self):
    return self.data.get("layers", [])

  def updateLayerList(self):
    layers = []

    # DEM and Vector layers
    for layer in getLayersInProject():
      layerType = layer.type()
      if layerType == QgsMapLayer.VectorLayer:
        geomType = {QgsWkbTypes.PointGeometry: q3dconst.TYPE_POINT,
                    QgsWkbTypes.LineGeometry: q3dconst.TYPE_LINESTRING,
                    QgsWkbTypes.PolygonGeometry: q3dconst.TYPE_POLYGON,
                    QgsWkbTypes.UnknownGeometry: None,
                    QgsWkbTypes.NullGeometry: None}[layer.geometryType()]

      elif layerType == QgsMapLayer.RasterLayer and layer.providerType() == "gdal" and layer.bandCount() == 1:
        geomType = q3dconst.TYPE_DEM
      else:
        geomType = q3dconst.TYPE_IMAGE
        continue

      if geomType is not None:
        item = self.getItemByLayerId(layer.id())
        if item:
          layers.append(item)
        else:
          layers.append({"layerId": layer.id(),
                         "name": layer.name(),
                         "geomType": geomType,
                         "properties": None,
                         "visible": False})

    # DEM provider plugins
    for plugin in self.pluginManager.demProviderPlugins():
      layerId = "plugin:" + plugin.providerId()
      item = self.getItemByLayerId(layerId)
      if item:
        layers.append(item)
      else:
        layers.append({"layerId": layerId,
                       "name": plugin.providerName(),
                       "geomType": q3dconst.TYPE_DEM,
                       "properties": None,
                       "visible": False})

    # Flat plane
    layerId = "FLAT"
    item = self.getItemByLayerId(layerId)
    if item:
      layers.append(item)
    else:
      layers.append({"layerId": layerId,
                     "name": "Flat Plane",
                     "geomType": q3dconst.TYPE_DEM,
                     "properties": None,
                     "visible": False})

    # update id and jsLayerId
    for index, layer in enumerate(layers):
      layer["id"] = index   #TODO: index
      layer["jsLayerId"] = index      # "{}_{}".format(itemId, layerId[:8])

    self.data["layers"] = layers

  def getItemByLayerId(self, layerId):
    for layer in self.data.get("layers", []):
      if layer["layerId"] == layerId:
        return layer
    return None
