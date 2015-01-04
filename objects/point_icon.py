# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                             -------------------
        begin                : 2015-01-03
        copyright            : (C) 2015 Minoru Akagi
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
from qgis.core import QGis
from Qgis2threejs.stylewidget import StyleWidget

def geometryType():
  return QGis.Point

def objectTypeNames():
  return ["Icon"]

def setupWidgets(ppage, mapTo3d, layer, type_index=0):
  filterString = "Images (*.png *.jpg *.gif *.bmp);;All files (*.*)"

  ppage.initStyleWidgets(color=False)
  ppage.addStyleWidget(StyleWidget.FILEPATH, {"name": "Image file", "layer": layer, "filterString": filterString})
  ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Scale", "defaultValue": 1, "layer": layer})

def write(writer, layer, feat):
  vals = feat.propValues()
  image_path = vals[0]
  scale = float(vals[1])
  mat = layer.materialManager.getSpriteIndex(image_path, feat.transparency())
  writer.writeFeature({"m": mat, "pts": feat.geom.asList(), "scale": scale})
