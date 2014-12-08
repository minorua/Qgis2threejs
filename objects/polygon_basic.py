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
from Qgis2threejs.stylewidget import StyleWidget

def geometryType():
  return QGis.Polygon

def objectTypeNames():
  return ["Extruded", "Overlay"]

def setupForm(ppage, mapTo3d, layer, type_index=0):
  defaultValueZ = 0.5 / mapTo3d.multiplierZ

  ppage.colorWidget.setup()
  ppage.transparencyWidget.setup()

  styleCount = 0
  if type_index == 0:   # Extruded
    ppage.styleWidgets[0].setup(StyleWidget.FIELD_VALUE, "Height", "Value", defaultValueZ, layer)
    styleCount = 1

  for i in range(styleCount, ppage.STYLE_MAX_COUNT):
    ppage.styleWidgets[i].hide()

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


def write(writer, feat):
  mat = writer.materialManager.getMeshLambertIndex(feat.color(), feat.transparency())
  vals = feat.propValues()
  d = {"m": mat}

  if feat.prop.type_index == 1:  # Overlay
    gons = []
    triangles = Triangles()
    for polygon in feat.polygons:
      boundary = polygon[0]
      if len(polygon) == 1 and len(boundary) == 4:
        triangles.addTriangle(boundary[0], boundary[2], boundary[1])    # vertex order should be counter-clockwise
      else:
        gons.append(polygon)
    if len(triangles.vertices):
      d["triangles"] = {"v": map(lambda pt: [pt.x, pt.y], triangles.vertices), "f": triangles.faces}
  else:
    gons = feat.polygons

  polygons = []
  zs = []
  for polygon in gons:
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
    d["h"] = feat.relativeHeight() * writer.context.mapTo3d.multiplierZ

  if len(feat.centroids):
    d["centroids"] = map(lambda pt: [pt.x, pt.y, pt.z], feat.centroids)
  writer.writeFeature(d)
