# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
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
  return ["Extruded"]

def setupForm(dialog, mapTo3d, layer, type_index=0):
  numeric_fields = None
  dialog.heightWidget.setup(layer=layer, fieldNames=numeric_fields)
  dialog.colorWidget.setup()
  dialog.transparencyWidget.setup()

  defaultValueZ = 0.5 / mapTo3d.multiplierZ
  dialog.styleWidgets[0].setup(StyleWidget.FIELD_VALUE, "Height", "Value", defaultValueZ, layer, numeric_fields)
  styleCount = 1
  for i in range(styleCount, dialog.STYLE_MAX_COUNT):
    dialog.styleWidgets[i].hide()

def write(writer, boundaries, properties, layer=None, f=None):
  mat = writer.materialManager.getMeshLambertIndex(properties.color(layer, f), properties.transparency(layer, f))
  vals = properties.values(f)
  h = float(vals[0]) * writer.context.mapTo3d.multiplierZ
  bnds = []
  zsum = zcount = 0
  for boundary in boundaries:
    bnds.append("[%s]" % ",".join(map(lambda pt: "[%f,%f]" % (pt.x, pt.y), boundary)))
    zsum += sum(map(lambda pt: pt.z, boundary), -boundary[0].z)
    zcount += len(boundary) - 1
  z = zsum / zcount
  writer.write("polygons.push({m:%d,z:%f,h:%f,bnds:[%s]});\n" % (mat, z, h, ",".join(bnds)))
