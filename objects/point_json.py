# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
                             -------------------
        begin                : 2014-01-19
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
json_pathes = []  #TODO: move into writer. moduleData["json_pathes"]?

def geometryType():
  return QGis.Point

def objectTypeNames():
  return ["JSON model"]

def setupForm(dialog, mapTo3d, layer, type_index=0):
  numeric_fields = None
  dialog.heightWidget.setup(layer=layer, fieldNames=numeric_fields)
  dialog.colorWidget.hide()
  dialog.transparencyWidget.hide()

  dialog.styleWidgets[0].setup(StyleWidget.FILEPATH, "JSON file", "Path", "", layer, None)
  dialog.styleWidgets[1].setup(StyleWidget.FIELD_VALUE, "Scale", "Value", 1, layer, numeric_fields)
  dialog.styleWidgets[2].setup(StyleWidget.FIELD_VALUE, "Rotation (x)", "Value (Degrees)", 90, layer, numeric_fields)
  dialog.styleWidgets[3].setup(StyleWidget.FIELD_VALUE, "Rotation (z)", "Value (Degrees)", 0, layer, numeric_fields)
  styleCount = 4
  for i in range(styleCount, dialog.STYLE_MAX_COUNT):
    dialog.styleWidgets[i].hide()

def write(writer, feat):
  mapTo3d = writer.context.mapTo3d
  vals = feat.propValues()
  json_path = vals[0]
  scale = float(vals[1])
  rotationX = float(vals[2])
  rotationZ = float(vals[3])
  if json_path in json_pathes:
    index = json_pathes.index(json_path)
  else:
    index = len(json_pathes)
    with open(json_path) as f:
      json = f.read().replace("\\", "\\\\").replace("'", "\\'").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
    writer.write("jsons[%d] = '%s';\n" % (index, json))
    json_pathes.append(json_path)
  writer.writeFeature({"json_index": index, "pts": feat.pointsAsList(), "rotateX": rotationX, "rotateY": rotationZ, "scale": scale})
