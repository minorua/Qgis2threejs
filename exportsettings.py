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
import qgis2threejstools as tools
from qgis2threejstools import logMessage
from settings import def_vals


class ExportSettings:

  # export mode
  PLAIN_SIMPLE = 0
  PLAIN_MULTI_RES = 1
  SPHERE = 2

  def __init__(self, settings, canvas, pluginManager, localBrowsingMode=True):
    self.data = settings
    self.timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

    # output html file path
    htmlfilename = settings.get("OutputFilename")
    if not htmlfilename:
      htmlfilename = tools.temporaryOutputDir() + "/%s.html" % self.timestamp
    self.htmlfilename = htmlfilename
    self.path_root = os.path.splitext(htmlfilename)[0]
    self.htmlfiletitle = os.path.basename(self.path_root)
    self.title = self.htmlfiletitle

    # load configuration of the template
    self.templateName = settings.get("Template", "")
    templatePath = os.path.join(tools.templateDir(), self.templateName)
    self.templateConfig = tools.getTemplateConfig(templatePath)

    # MapTo3D object
    world = settings.get(ObjectTreeItem.ITEM_WORLD, {})
    baseSize = world.get("lineEdit_BaseSize", def_vals.baseSize)
    verticalExaggeration = world.get("lineEdit_zFactor", def_vals.zExaggeration)
    verticalShift = world.get("lineEdit_zShift", def_vals.zShift)
    self.mapTo3d = MapTo3D(canvas, float(baseSize), float(verticalExaggeration), float(verticalShift))

    self.coordsInWGS84 = world.get("radioButton_WGS84", False)

    self.canvas = canvas
    self.mapSettings = canvas.mapSettings() if QGis.QGIS_VERSION_INT >= 20300 else canvas.mapRenderer()
    self.baseExtent = RotatedRect.fromMapSettings(self.mapSettings)

    self.pluginManager = pluginManager
    self.localBrowsingMode = localBrowsingMode

    self.crs = self.mapSettings.destinationCrs()

    wgs84 = QgsCoordinateReferenceSystem(4326)
    transform = QgsCoordinateTransform(self.crs, wgs84)
    self.wgs84Center = transform.transform(self.baseExtent.center())

    controls = settings.get(ObjectTreeItem.ITEM_CONTROLS, {})
    self.controls = controls.get("comboBox_Controls")
    if not self.controls:
      self.controls = QSettings().value("/Qgis2threejs/lastControls", "OrbitControls.js", type=unicode)

    self.demProvider = None
    self.quadtree = None

    if self.templateConfig.get("type") == "sphere":
      self.exportMode = ExportSettings.SPHERE
      return

    demProperties = settings.get(ObjectTreeItem.ITEM_DEM, {})
    self.demProvider = self.demProviderByLayerId(demProperties["comboBox_DEMLayer"])

    if demProperties.get("radioButton_Simple", False):
      self.exportMode = ExportSettings.PLAIN_SIMPLE
    else:
      self.exportMode = ExportSettings.PLAIN_MULTI_RES
      self.quadtree = createQuadTree(self.baseExtent, demProperties)

  def get(self, key, default=None):
    return self.data.get(key, default)

  def checkValidity(self):
    """return valid as bool, err_msg as str"""
    # check validity of settings
    if self.exportMode == ExportSettings.PLAIN_MULTI_RES and self.quadtree is None:
      return False, u"Focus point/area is not selected."
    return True, ""

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
