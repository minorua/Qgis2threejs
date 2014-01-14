# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
                             -------------------
        begin                : 2014-01-11
        copyright            : (C) 2014 by Minoru Akagi
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

def geometryType():
  return QGis.Point

def objectTypeNames():
  return ["Sphere", "Cylinder", "Cube", "Cone"]

def setupForm(dialog, mapTo3d, layer, obj_type=""):
  numeric_fields = None
  dialog.colorWidget.setup()
  dialog.heightWidget.setup(layer, numeric_fields)

  defaultValue = 0.5 / mapTo3d.multiplier
  defaultValueZ = 0.5 / mapTo3d.multiplierZ
  if obj_type == "Sphere":
    dialog.styleWidgets[0].setup("Radius", "Value", defaultValue, layer, numeric_fields)
    styleCount = 1
  elif obj_type in ["Cylinder", "Cone"]:
    dialog.styleWidgets[0].setup("Radius", "Value", defaultValue, layer, numeric_fields)
    dialog.styleWidgets[1].setup("Height", "Value", defaultValueZ, layer, numeric_fields)
    styleCount = 2
  elif obj_type == "Cube":
    dialog.styleWidgets[0].setup("Width", "Value", defaultValue, layer, numeric_fields)
    dialog.styleWidgets[1].setup("Depth", "Value", defaultValue, layer, numeric_fields)
    dialog.styleWidgets[2].setup("Height", "Value", defaultValueZ, layer, numeric_fields)
    styleCount = 3
  else:
    styleCount = 0
  for i in range(styleCount, dialog.STYLE_MAX_COUNT):
    dialog.styleWidgets[i].hide()

def generateJS(mapTo3d, pt, mat, properties, f=None):
  vals = properties.values(f)
  if properties.obj_typename == "Sphere": #VectorObjectType.SPHERE:
    r = float(vals[0]) * mapTo3d.multiplier
    return 'points.push({type:"sphere",m:%d,pt:[%f,%f,%f],r:%f});' % (mat, pt.x, pt.y, pt.z, r)
  elif properties.obj_typename in ["Cylinder", "Cone"]:
    rb = float(vals[0]) * mapTo3d.multiplier
    rt = 0 if properties.obj_typename == "Cone" else rb
    h = float(vals[1]) * mapTo3d.multiplierZ
    z = pt.z + h / 2
    return 'points.push({type:"cylinder",m:%d,pt:[%f,%f,%f],rt:%f,rb:%f,h:%f,rotateX:Math.PI*%d/180});' % (mat, pt.x, pt.y, z, rt, rb, h, 90)
  elif properties.obj_typename == "Cube": #VectorObjectType.CUBE:
    w = float(vals[0]) * mapTo3d.multiplier
    d = float(vals[1]) * mapTo3d.multiplier
    h = float(vals[2]) * mapTo3d.multiplierZ
    z = pt.z + h / 2
    return 'points.push({type:"cube",m:%d,pt:[%f,%f,%f],w:%f,d:%f,h:%f,rotateX:Math.PI*%d/180});' % (mat, pt.x, pt.y, z, w, d, h, 90)
  return ""
