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
  return QGis.Line

def objectTypeNames():
  return ["Line"]

def setupForm(dialog, mapTo3d, layer, type_index=0):
  numeric_fields = None
  dialog.heightWidget.setup(layer=layer, fieldNames=numeric_fields)
  dialog.colorWidget.setup()
  dialog.transparencyWidget.setup()
  for i in range(dialog.STYLE_MAX_COUNT):
    dialog.styleWidgets[i].hide()

def write(writer, feat):
  mat = writer.materialManager.getLineBasicIndex(feat.color(), feat.transparency())
  writer.writeFeature({"m": mat, "lines": feat.linesAsList()})
