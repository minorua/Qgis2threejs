# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
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
  return QGis.Point

def objectTypeNames():
  return ["Sphere", "Cylinder", "Cube", "Cone"]

def setupForm(dialog, mapTo3d, layer, type_index=0):
  numeric_fields = None
  dialog.colorWidget.setup()
  dialog.heightWidget.setup(layer=layer, fieldNames=numeric_fields)

  defaultValue = 0.5 / mapTo3d.multiplier
  defaultValueZ = 0.5 / mapTo3d.multiplierZ
  if type_index == 0:  # Sphere
    dialog.styleWidgets[0].setup(StyleWidget.FIELD_VALUE, "Radius", "Value", defaultValue, layer, numeric_fields)
    styleCount = 1
  elif type_index in [1, 3]: # Cylinder, Cone
    dialog.styleWidgets[0].setup(StyleWidget.FIELD_VALUE, "Radius", "Value", defaultValue, layer, numeric_fields)
    dialog.styleWidgets[1].setup(StyleWidget.FIELD_VALUE, "Height", "Value", defaultValueZ, layer, numeric_fields)
    styleCount = 2
  elif type_index == 2:  # Cube
    dialog.styleWidgets[0].setup(StyleWidget.FIELD_VALUE, "Width", "Value", defaultValue, layer, numeric_fields)
    dialog.styleWidgets[1].setup(StyleWidget.FIELD_VALUE, "Depth", "Value", defaultValue, layer, numeric_fields)
    dialog.styleWidgets[2].setup(StyleWidget.FIELD_VALUE, "Height", "Value", defaultValueZ, layer, numeric_fields)
    styleCount = 3
  else:
    styleCount = 0
  for i in range(styleCount, dialog.STYLE_MAX_COUNT):
    dialog.styleWidgets[i].hide()

def write(writer, pt, properties, layer=None, f=None):
  mat = writer.materialManager.getMeshLambertIndex(properties.color(layer, f))
  mapTo3d = writer.context.mapTo3d
  vals = properties.values(f)
  if properties.type_index == 0:  # Sphere
    r = float(vals[0]) * mapTo3d.multiplier
    if r != 0:
      writer.write('points.push({type:"sphere",m:%d,pt:[%f,%f,%f],r:%f});\n' % (mat, pt.x, pt.y, pt.z, r))
  elif properties.type_index in [1, 3]: # Cylinder, Cone
    rb = float(vals[0]) * mapTo3d.multiplier
    rt = 0 if properties.type_index == 3 else rb
    h = float(vals[1]) * mapTo3d.multiplierZ
    z = pt.z + h / 2
    writer.write('points.push({type:"cylinder",m:%d,pt:[%f,%f,%f],rt:%f,rb:%f,h:%f,rotateX:Math.PI*%d/180});\n' % (mat, pt.x, pt.y, z, rt, rb, h, 90))
  elif properties.type_index == 2:  # Cube
    w = float(vals[0]) * mapTo3d.multiplier
    d = float(vals[1]) * mapTo3d.multiplier
    h = float(vals[2]) * mapTo3d.multiplierZ
    z = pt.z + h / 2
    writer.write('points.push({type:"cube",m:%d,pt:[%f,%f,%f],w:%f,d:%f,h:%f,rotateX:Math.PI*%d/180});\n' % (mat, pt.x, pt.y, z, w, d, h, 90))
