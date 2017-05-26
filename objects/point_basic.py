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
from Qgis2threejs.qgis2threejstools import logMessage
from Qgis2threejs.stylewidget import StyleWidget


def geometryType():
  return QgsWkbTypes.PointGeometry


def objectTypeNames():
  return ["Sphere", "Cylinder", "Cone", "Box", "Disk"]


def setupWidgets(ppage, mapTo3d, layer, type_index=0):
  defaultValue = 0.6 / mapTo3d.multiplier
  defaultValueZ = 0.6 / mapTo3d.multiplierZ

  ppage.initStyleWidgets()
  if type_index == 0:  # Sphere
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": defaultValue, "layer": layer})
  elif type_index in [1, 2]:  # Cylinder, Cone
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": defaultValue, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": defaultValueZ, "layer": layer})
  elif type_index == 3:  # Box
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Width", "defaultValue": defaultValue, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Depth", "defaultValue": defaultValue, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": defaultValueZ, "layer": layer})
  elif type_index == 4:  # Disk
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": defaultValue, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Dip", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Dip direction", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": layer})


def write(settings, layer, feat):
  mapTo3d = settings.mapTo3d()
  vals = feat.propValues()
  mat = layer.materialManager.getMeshLambertIndex(vals[0], vals[1])
  pts = feat.geom.asList()
  if feat.prop.type_index == 0:  # Sphere
    r = float(vals[2]) * mapTo3d.multiplier
    if r:
      return {"pts": pts, "r": r}, mat
    else:
      logMessage(u"Sphere with zero radius not exported")

  elif feat.prop.type_index in [1, 2]:  # Cylinder, Cone
    rb = float(vals[2]) * mapTo3d.multiplier
    rt = 0 if feat.prop.type_index == 2 else rb
    h = float(vals[3]) * mapTo3d.multiplierZ
    return {"pts": pts, "rt": rt, "rb": rb, "h": h, "rotateX": 90}, mat

  elif feat.prop.type_index == 3:  # Box
    w = float(vals[2]) * mapTo3d.multiplier
    d = float(vals[3]) * mapTo3d.multiplier
    h = float(vals[4]) * mapTo3d.multiplierZ
    return {"pts": pts, "w": w, "d": d, "h": h, "rotateX": 90}, mat

  elif feat.prop.type_index == 4:  # Disk
    r = float(vals[2]) * mapTo3d.multiplier
    d = float(vals[3])
    dd = float(vals[4])

    # take map rotation into account
    rotation = settings.baseExtent.rotation()
    if rotation:
      dd = (dd + rotation) % 360

    return {"pts": pts, "r": r, "d": d, "dd": dd}, mat

  return None, None
