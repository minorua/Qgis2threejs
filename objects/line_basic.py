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

def setupForm(ppage, mapTo3d, layer, type_index=0):
  defaultValue = 0.5 / mapTo3d.multiplier

  ppage.colorWidget.setup()
  ppage.transparencyWidget.setup()

  if type_index in [1, 2]:  # Pipe or Cone
    ppage.styleWidgets[0].setup(StyleWidget.FIELD_VALUE, "Radius", "Value", defaultValue, layer)
    styleCount = 1
  else:
    styleCount = 0
  for i in range(styleCount, ppage.STYLE_MAX_COUNT):
    ppage.styleWidgets[i].hide()

def write(writer, feat):
  mapTo3d = writer.context.mapTo3d
  if feat.prop.type_index in [0, 3]:   # Line or Profile
    if feat.prop.type_index == 0:
      mat = writer.materialManager.getLineBasicIndex(feat.color(), feat.transparency())
    else:
      mat = writer.materialManager.getMeshLambertIndex(feat.color(), feat.transparency(), doubleSide=True)
    writer.writeFeature({"m": mat, "lines": feat.linesAsList()})
    return

  # Pipe or Cone
  vals = feat.propValues()
  rb = float(vals[0]) * mapTo3d.multiplier
  if rb != 0:
    mat = writer.materialManager.getMeshLambertIndex(feat.color(), feat.transparency())
    rt = 0 if feat.prop.type_index == 2 else rb
    writer.writeFeature({"m": mat, "lines": feat.linesAsList(), "rt": rt, "rb": rb})
