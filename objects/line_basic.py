# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                             -------------------
        begin                : 2014-01-11
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
  return QGis.Line

def objectTypeNames():
  return ["Line", "Pipe", "Cone", "Profile"]

def setupWidgets(ppage, mapTo3d, layer, type_index=0):
  defaultValue = 0.6 / mapTo3d.multiplier

  ppage.initStyleWidgets()
  if type_index in [1, 2]:  # Pipe or Cone
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": defaultValue, "layer": layer})

def write(writer, layer, feat):
  mapTo3d = writer.settings.mapTo3d
  vals = feat.propValues()
  if feat.prop.type_index in [0, 3]:   # Line or Profile
    if feat.prop.type_index == 0:
      mat = layer.materialManager.getLineBasicIndex(vals[0], vals[1])
    else:
      mat = layer.materialManager.getFlatMeshLambertIndex(vals[0], vals[1], doubleSide=True)
    writer.writeFeature({"m": mat, "lines": feat.geom.asList()})
    return

  # Pipe or Cone
  rb = float(vals[2]) * mapTo3d.multiplier
  if rb != 0:
    mat = layer.materialManager.getMeshLambertIndex(vals[0], vals[1])
    rt = 0 if feat.prop.type_index == 2 else rb
    writer.writeFeature({"m": mat, "lines": feat.geom.asList(), "rt": rt, "rb": rb})
