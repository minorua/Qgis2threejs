# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
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
from Qgis2threejs.stylewidget import StyleWidget, HeightWidgetFunc, LabelHeightWidgetFunc

def geometryType():
  return QGis.Polygon

def objectTypeNames():
  return ["Extruded", "Overlay"]

def setupWidgets(ppage, mapTo3d, layer, type_index=0):
  defaultValueZ = 0.6 / mapTo3d.multiplierZ

  # style widgets
  ppage.initStyleWidgets()
  if type_index == 0:   # Extruded
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": defaultValueZ, "layer": layer})
  else:   # Overlay
    ppage.addStyleWidget(StyleWidget.BORDER_COLOR)

  # label height widget
  if type_index == 0:
    item_text = ["Height from top", "Height from bottom"]
  else:
    item_text = ["Height from overlay", "Height from DEM"]

  comboBox = ppage.labelHeightWidget.comboBox
  comboBox.clear()
  comboBox.addItem(item_text[0], LabelHeightWidgetFunc.RELATIVE_TO_TOP)
  comboBox.addItem(item_text[1], LabelHeightWidgetFunc.RELATIVE)
  comboBox.addItem("Fixed value", HeightWidgetFunc.ABSOLUTE)
  if layer:
    ppage.labelHeightWidget.addFieldNameItems(layer)


class Triangles:
  def __init__(self):
    self.vertices = []
    self.faces = []
    self.vdict = {}   # dict to find whether a vertex already exists: [y][x] = vertex index

  def addTriangle(self, v1, v2, v3):
    vi1 = self._vertexIndex(v1)
    vi2 = self._vertexIndex(v2)
    vi3 = self._vertexIndex(v3)
    self.faces.append([vi1, vi2, vi3])

  def _vertexIndex(self, v):
    x_dict = self.vdict.get(v.y)
    if x_dict:
      vi = x_dict.get(v.x)
      if vi is not None:
        return vi
    vi = len(self.vertices)
    self.vertices.append(v)
    if x_dict:
      x_dict[v.x] = vi
    else:
      self.vdict[v.y] = {v.x: vi}
    return vi


def write(writer, layer, feat):
  vals = feat.propValues()
  d = {"m": layer.materialManager.getMeshLambertIndex(feat.color(), feat.transparency())}
  polygons = []
  zs = []
  for polygon in feat.geom.polygons:
    bnds = []
    zsum = zcount = 0
    for boundary in polygon:
      bnds.append(map(lambda pt: [pt.x, pt.y], boundary))
      zsum += sum(map(lambda pt: pt.z, boundary), -boundary[0].z)
      zcount += len(boundary) - 1
    polygons.append(bnds)
    zs.append(zsum / zcount)
  d["polygons"] = polygons

  if feat.prop.type_index == 0:  # Extruded
    d["zs"] = zs
    d["h"] = float(vals[0]) * writer.context.mapTo3d.multiplierZ

  else:   # Overlay
    polygons = []
    triangles = Triangles()
    for polygon in feat.geom.split_polygons:
      boundary = polygon[0]
      if len(polygon) == 1 and len(boundary) == 4:
        triangles.addTriangle(boundary[0], boundary[2], boundary[1])    # vertex order should be counter-clockwise
      else:
        bnds = [map(lambda pt: [pt.x, pt.y], bnd) for bnd in polygon]
        polygons.append(bnds)

    if triangles.vertices:
      d["triangles"] = {"v": map(lambda pt: [pt.x, pt.y], triangles.vertices), "f": triangles.faces}
    if polygons:
      d["split_polygons"] = polygons
    d["h"] = feat.relativeHeight() * writer.context.mapTo3d.multiplierZ
    if vals[0] is not None:
      d["b"] = layer.materialManager.getLineBasicIndex(vals[0], feat.transparency())

  if feat.geom.centroids:
    d["centroids"] = map(lambda pt: [pt.x, pt.y, pt.z], feat.geom.centroids)

  writer.writeFeature(d)
