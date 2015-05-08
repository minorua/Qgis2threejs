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
from Qgis2threejs.stylewidget import StyleWidget, HeightWidgetFunc

def geometryType():
  return QGis.Line

def objectTypeNames():
  return ["Line", "Pipe", "Cone", "Profile", "Box"]     # TODO: move Box before Profile

def setupWidgets(ppage, mapTo3d, layer, type_index=0):
  defaultValue = 0.6 / mapTo3d.multiplier

  ppage.initStyleWidgets()
  if type_index in [1, 2]:  # Pipe or Cone
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": defaultValue, "layer": layer})
  elif type_index == 3:     # Profile
    opt = {"name": "Bottom Z",
           "layer": layer,
           "defaultItem": HeightWidgetFunc.ABSOLUTE}
    ppage.addStyleWidget(StyleWidget.HEIGHT, opt)
  elif type_index == 4:     # Box
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Width", "defaultValue": defaultValue, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": defaultValue, "layer": layer})

def layerProperties(writer, layer):
  p = {}
  prop = layer.prop
  if prop.type_index == 3:      # Profile
    # altitude mode
    p["am"] = "relative" if prop.isHeightRelativeToDEM() else "absolute"

    # altitude mode of bottom
    cb = prop.properties["styleWidget2"]["comboData"]
    isBRelative = (cb == HeightWidgetFunc.RELATIVE or cb >= HeightWidgetFunc.FIRST_ATTR_REL)
    p["bam"] = "relative" if isBRelative else "absolute"
  return p

def write(writer, layer, feat):
  mapTo3d = writer.settings.mapTo3d
  type_index = feat.prop.type_index
  vals = feat.propValues()

  if type_index == 0:   # Line
    mat = layer.materialManager.getLineBasicIndex(vals[0], vals[1])
    writer.writeFeature({"m": mat, "lines": feat.geom.asList()})

  elif type_index in [1, 2]:    # Pipe or Cone
    rb = float(vals[2]) * mapTo3d.multiplier
    if rb != 0:
      mat = layer.materialManager.getMeshLambertIndex(vals[0], vals[1])
      rt = 0 if type_index == 2 else rb
      writer.writeFeature({"m": mat, "lines": feat.geom.asList(), "rt": rt, "rb": rb})

  elif type_index == 3:   # Profile
    d = {"m": layer.materialManager.getFlatMeshLambertIndex(vals[0], vals[1], doubleSide=True)}
    if feat.prop.isHeightRelativeToDEM():
      d["h"] = feat.relativeHeight() * mapTo3d.multiplierZ
      d["lines"] = feat.geom.asList2()
    else:
      d["lines"] = feat.geom.asList()

    d["bh"] = float(vals[2]) * mapTo3d.multiplierZ
    writer.writeFeature(d)

  elif type_index == 4:   # Box
    mat = layer.materialManager.getMeshLambertIndex(vals[0], vals[1])
    w = float(vals[2]) * mapTo3d.multiplier
    h = float(vals[3]) * mapTo3d.multiplier
    writer.writeFeature({"m": mat, "lines": feat.geom.asList(), "w": w, "h": h})
