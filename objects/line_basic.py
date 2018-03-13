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
from qgis.core import QgsWkbTypes
from Qgis2threejs.stylewidget import StyleWidget, HeightWidgetFunc


def geometryType():
  return QgsWkbTypes.LineGeometry


def objectTypeNames():
  return ["Line", "Pipe", "Cone", "Box", "Profile"]


def setupWidgets(ppage, mapTo3d, layer, type_index=0):
  defaultValue = float("{0:.4g}".format(0.6 / mapTo3d.multiplier))

  ppage.initStyleWidgets()
  if type_index in [1, 2]:  # Pipe, Cone
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": defaultValue, "layer": layer})
  elif type_index == 3:     # Box
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Width", "defaultValue": defaultValue, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": defaultValue, "layer": layer})
  elif type_index == 4:     # Profile
    opt = {"name": "Lower Z",
           "layer": layer,
           "defaultItem": HeightWidgetFunc.ABSOLUTE}
    ppage.addStyleWidget(StyleWidget.HEIGHT, opt)


def layerProperties(settings, layer):
  p = {}
  if layer.prop.type_index == 4:      # Profile
    # altitude mode
    p["am"] = "relative" if layer.prop.isHeightRelativeToDEM() else "absolute"

    # altitude mode of bottom
    cb = layer.prop.properties["styleWidget2"]["comboData"]
    isBRelative = (cb == HeightWidgetFunc.RELATIVE or cb >= HeightWidgetFunc.FIRST_ATTR_REL)
    p["bam"] = "relative" if isBRelative else "absolute"
  return p


def material(settings, layer, feat):
  type_index = layer.prop.type_index
  if type_index == 0:   # Line
    return layer.materialManager.getLineBasicIndex(feat.values[0], feat.values[1])

  if type_index in [1, 2]:    # Pipe, Cone
    return layer.materialManager.getMeshLambertIndex(feat.values[0], feat.values[1])

  if type_index == 3:   # Box
    return layer.materialManager.getMeshLambertIndex(feat.values[0], feat.values[1])

  if type_index == 4:   # Profile
    return layer.materialManager.getFlatMeshLambertIndex(feat.values[0], feat.values[1], doubleSide=True)


def geometry(settings, layer, feat, geom):
  mapTo3d = settings.mapTo3d()
  type_index = layer.prop.type_index
  if type_index == 0:   # Line
    return {"lines": geom.asList()}

  if type_index in [1, 2]:    # Pipe, Cone
    rb = feat.values[2] * mapTo3d.multiplier
    rt = 0 if type_index == 2 else rb
    return {"lines": geom.asList(), "rt": rt, "rb": rb}

  if type_index == 3:   # Box
    w = feat.values[2] * mapTo3d.multiplier
    h = feat.values[3] * mapTo3d.multiplier
    return {"lines": geom.asList(), "w": w, "h": h}

  if type_index == 4:   # Profile
    d = {}
    if layer.prop.isHeightRelativeToDEM():
      d["h"] = feat.altitude * mapTo3d.multiplierZ
      d["lines"] = geom.asList2()
    else:
      d["lines"] = geom.asList()

    d["bh"] = feat.values[2] * mapTo3d.multiplierZ

    return d
