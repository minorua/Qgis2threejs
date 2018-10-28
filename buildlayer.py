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


class LayerBuilder:

  def __init__(self, settings, imageManager, layer, pathRoot=None, urlRoot=None, progress=None):
    self.settings = settings
    self.imageManager = imageManager

    self.layer = layer
    self.properties = layer.properties

    self.pathRoot = pathRoot
    self.urlRoot = urlRoot
    self.progress = progress or dummyProgress

  def build(self):
    pass

  def layerProperties(self):
    return {"name": self.layer.name,
            "queryable": 1,
            "visible": self.properties.get("checkBox_Visible", True) or self.pathRoot is None}  # always visible in preview


def dummyProgress(progress=None, statusMsg=None):
  pass
