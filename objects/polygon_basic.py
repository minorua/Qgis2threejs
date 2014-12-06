# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                             -------------------
        begin                : 2014-01-13
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
from qgis.core import QGis
from Qgis2threejs.stylewidget import StyleWidget

def geometryType():
  return QGis.Polygon

def objectTypeNames():
  return ["Extruded", "Overlay"]

def setupForm(ppage, mapTo3d, layer, type_index=0):
  defaultValueZ = 0.5 / mapTo3d.multiplierZ

  ppage.colorWidget.setup()
  ppage.transparencyWidget.setup()

  styleCount = 0
  if type_index == 0:   # Extruded
    ppage.styleWidgets[0].setup(StyleWidget.FIELD_VALUE, "Height", "Value", defaultValueZ, layer)
    styleCount = 1

  for i in range(styleCount, ppage.STYLE_MAX_COUNT):
    ppage.styleWidgets[i].hide()

def write(writer, feat):
  mat = writer.materialManager.getMeshLambertIndex(feat.color(), feat.transparency())
  vals = feat.propValues()

  polygons = []
  zs = []
  for polygon in feat.polygons:
    bnds = []
    zsum = zcount = 0
    for boundary in polygon:
      bnds.append(map(lambda pt: [pt.x, pt.y], boundary))
      zsum += sum(map(lambda pt: pt.z, boundary), -boundary[0].z)
      zcount += len(boundary) - 1
    polygons.append(bnds)
    zs.append(zsum / zcount)
  d = {"m": mat, "polygons": polygons}

  if feat.prop.type_index == 0:  # Extruded
    d["zs"] = zs
    d["h"] = float(vals[0]) * writer.context.mapTo3d.multiplierZ

  else:   # Overlay
    d["h"] = feat.relativeHeight() * writer.context.mapTo3d.multiplierZ

  if len(feat.centroids):
    d["centroids"] = map(lambda pt: [pt.x, pt.y, pt.z], feat.centroids)
  writer.writeFeature(d)
