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
from Qgis2threejs.stylewidget import StyleWidget, ColorWidgetFunc, HeightWidgetFunc, LabelHeightWidgetFunc, OptionalColorWidgetFunc, ColorTextureWidgetFunc

def geometryType():
  return QGis.Polygon

def objectTypeNames():
  return ["Extruded", "Overlay"]

def setupWidgets(ppage, mapTo3d, layer, type_index=0):
  defaultValueZ = 0.6 / mapTo3d.multiplierZ

  # style widgets
  if type_index == 0:   # Extruded
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": defaultValueZ, "layer": layer})
  else:   # Overlay
    ppage.initStyleWidgets(color=False, transparency=False)
    ppage.addStyleWidget(StyleWidget.COLOR_TEXTURE)
    ppage.addStyleWidget(StyleWidget.TRANSPARENCY)

    opt = {"name": "Border color",
           "itemText": {OptionalColorWidgetFunc.NONE: "(No border)"},
           "defaultItem": ColorWidgetFunc.FEATURE}
    ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

    opt = {"name": "Side color",
           "itemText": {OptionalColorWidgetFunc.NONE: "(No side)",
                        ColorWidgetFunc.FEATURE: "Border color of feature style"}}
    ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

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
    ppage.labelHeightWidget.addFieldNames(layer)


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

  d = {"polygons": polygons}

  if feat.prop.type_index == 0:  # Extruded
    d["m"] = layer.materialManager.getMeshLambertIndex(vals[0], vals[1])
    d["zs"] = zs
    d["h"] = float(vals[2]) * writer.settings.mapTo3d.multiplierZ

  else:   # Overlay
    if vals[0] == ColorTextureWidgetFunc.MAP_CANVAS:
      d["m"] = layer.materialManager.getCanvasImageIndex(vals[1])
    elif isinstance(vals[0], list):   # LAYER
      size = writer.settings.mapSettings.outputSize()
      extent = writer.settings.baseExtent
      d["m"] = layer.materialManager.getLayerImageIndex(vals[0], size.width(), size.height(), extent, vals[1])
    else:
      d["m"] = layer.materialManager.getMeshLambertIndex(vals[0], vals[1], True)

    if vals[2] is not None:
      d["mb"] = layer.materialManager.getLineBasicIndex(vals[2], vals[1])

    if vals[3] is not None:
      d["ms"] = layer.materialManager.getMeshLambertIndex(vals[3], vals[1], True)

    d["h"] = feat.relativeHeight() * writer.settings.mapTo3d.multiplierZ

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

  if feat.geom.centroids:
    d["centroids"] = map(lambda pt: [pt.x, pt.y, pt.z], feat.geom.centroids)

  writer.writeFeature(d)
