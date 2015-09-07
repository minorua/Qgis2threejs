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
from Qgis2threejs.geometry import Triangles


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

    mapSettings = ppage.dialog.iface.mapCanvas().mapSettings() if QGis.QGIS_VERSION_INT >= 20300 else None
    ppage.addStyleWidget(StyleWidget.COLOR_TEXTURE, {"mapSettings": mapSettings})
    ppage.addStyleWidget(StyleWidget.TRANSPARENCY)

    opt = {"name": "Border color",
           "itemText": {OptionalColorWidgetFunc.NONE: "(No border)"},
           "defaultItem": ColorWidgetFunc.FEATURE}
    ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

    opt = {"name": "Side",
           "connectTo": [ppage.styleWidgets[4], ppage.styleWidgets[5]]}
    ppage.addStyleWidget(StyleWidget.CHECKBOX, opt)

    opt = {"name": "Side color",
           "itemText": {OptionalColorWidgetFunc.NONE: None,
                        OptionalColorWidgetFunc.FEATURE: "Feature style (border)"}}
    ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

    opt = {"name": "Side lower Z",
           "layer": layer,
           "defaultItem": HeightWidgetFunc.ABSOLUTE}
    ppage.addStyleWidget(StyleWidget.HEIGHT, opt)

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


def layerProperties(writer, layer):
  p = {}
  prop = layer.prop
  if prop.type_index == 1:      # Overlay
    p["am"] = "relative" if prop.isHeightRelativeToDEM() else "absolute"    # altitude mode

    # altitude mode of bottom of side
    cb = prop.properties["styleWidget5"]["comboData"]
    isSbRelative = (cb == HeightWidgetFunc.RELATIVE or cb >= HeightWidgetFunc.FIRST_ATTR_REL)
    p["sbm"] = "relative" if isSbRelative else "absolute"
  return p


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

    # border
    if vals[2] is not None:
      d["mb"] = layer.materialManager.getLineBasicIndex(vals[2], vals[1])

    # side
    if vals[3]:
      d["ms"] = layer.materialManager.getMeshLambertIndex(vals[4], vals[1], doubleSide=True)

      # bottom height of side
      d["sb"] = vals[5] * writer.settings.mapTo3d.multiplierZ

    # If height mode is relative to DEM, height from DEM. Otherwise from zero altitude.
    # Vertical shift is not considered (will be shifted in JS).
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
