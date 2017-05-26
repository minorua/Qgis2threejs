# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
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
from qgis.core import QgsProject, QgsRectangle

from . import gdal2threejs
from .datamanager import ImageManager, ModelManager, MaterialManager
from .propertyreader import DEMPropertyReader
from .qgis2threejscore import GDALDEMProvider
from . import qgis2threejstools as tools
from .qgis2threejstools import logMessage


class LayerExporter:

  def __init__(self, settings, imageManager, progress=None):
    self.settings = settings
    self.imageManager = imageManager
    self.materialManager = MaterialManager()    #TODO: takes imageManager
    self.progress = progress or dummyProgress

  def export(self, layerId, properties, jsLayerId, visible=True):
    pass


def dummyProgress(progress=None, statusMsg=None):
  pass
