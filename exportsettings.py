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

from PyQt4.QtCore import QSettings
from qgis.core import QGis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsMapLayerRegistry

from rotatedrect import RotatedRect
from qgis2threejscore import ObjectTreeItem, MapTo3D, GDALDEMProvider, FlatDEMProvider, createQuadTree
from qgis2threejstools import logMessage
from settings import def_vals
import qgis2threejstools as tools


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
      from pluginmanager import PluginManager
      self.pluginManager = PluginManager()

    self.data = {}
    self.timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

    self.templatePath = None

    self.htmlfilename = None
    self.path_root = None
    self.htmlfiletitle = None
    self.title = None

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
    return QSettings().value("/Qgis2threejs/lastControls", def_vals.controls, type=unicode)

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
    self.path_root = os.path.splitext(filepath)[0]
    self.htmlfiletitle = os.path.basename(self.path_root)
    self.title = self.htmlfiletitle

  def setMapCanvas(self, canvas):
    self.setMapSettings(canvas.mapSettings() if QGis.QGIS_VERSION_INT >= 20300 else canvas.mapRenderer())
    self.canvas = canvas

  def setMapSettings(self, settings):
    """settings: QgsMapSettings (QGIS >= 2.3) or QgsMapRenderer"""
    self.canvas = None
    self.mapSettings = settings

    self.baseExtent = RotatedRect.fromMapSettings(settings)
    self.crs = settings.destinationCrs()

  def demProvider(self):
    layerId = self.data.get(ObjectTreeItem.ITEM_DEM, {}).get("comboBox_DEMLayer", 0)
    return self.demProviderByLayerId(layerId)

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
      return u"Focus point/area is not selected."
    return None

  def demProviderByLayerId(self, id):
    if not id:
      return FlatDEMProvider()

    if id.startswith("plugin:"):
      provider = self.pluginManager.findDEMProvider(id[7:])
      if provider:
        return provider(str(self.crs.toWkt()))

      logMessage('Plugin "{0}" not found'.format(id))
      return FlatDEMProvider()

    else:
      layer = QgsMapLayerRegistry.instance().mapLayer(id)
      return GDALDEMProvider(layer.source(), str(self.crs.toWkt()), source_wkt=str(layer.crs().toWkt()))    # use CRS set to the layer in QGIS
