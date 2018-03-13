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
from qgis.core import QgsWkbTypes
from Qgis2threejs.stylewidget import StyleWidget, ColorWidgetFunc, HeightWidgetFunc, LabelHeightWidgetFunc, OptionalColorWidgetFunc, ColorTextureWidgetFunc
from Qgis2threejs.geometry import Triangles


def geometryType():
  return QgsWkbTypes.PolygonGeometry


def objectTypeNames():
  return ["Extruded", "Overlay"]


def setupWidgets(ppage, mapTo3d, layer, type_index=0):
  defaultValueZ = float("{0:.4g}".format(0.6 / mapTo3d.multiplierZ))

  # style widgets
  if type_index == 0:   # Extruded
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": defaultValueZ, "layer": layer})

    opt = {"name": "Border color",
           "itemText": {OptionalColorWidgetFunc.NONE: "(No border)"},
           "defaultItem": ColorWidgetFunc.FEATURE}
    ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

  else:   # Overlay
    ppage.initStyleWidgets(color=False, opacity=False)

    mapSettings = ppage.dialog.iface.mapCanvas().mapSettings()
    ppage.addStyleWidget(StyleWidget.COLOR_TEXTURE, {"mapSettings": mapSettings})
    ppage.addStyleWidget(StyleWidget.OPACITY)

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

  ppage.setupLabelHeightWidget([(LabelHeightWidgetFunc.RELATIVE_TO_TOP, item_text[0]),
                                (LabelHeightWidgetFunc.RELATIVE, item_text[1])])


#TODO
def layerProperties(settings, layer):
  p = {}
  prop = layer.prop
  if prop.type_index == 1:      # Overlay
    p["am"] = "relative" if prop.isHeightRelativeToDEM() else "absolute"    # altitude mode

    # altitude mode of bottom of side
    cb = prop.properties["styleWidget5"]["comboData"]
    isSbRelative = (cb == HeightWidgetFunc.RELATIVE or cb >= HeightWidgetFunc.FIRST_ATTR_REL)
    p["sbm"] = "relative" if isSbRelative else "absolute"
  return p


def material(settings, layer, feat):
  if layer.prop.type_index == 0:  # Extruded
    mat = {"face": layer.materialManager.getMeshLambertIndex(feat.values[0], feat.values[1])}

    # border
    if feat.values[3] is not None:
      mat["border"] = layer.materialManager.getLineBasicIndex(feat.values[3], feat.values[1])
    return mat

  # Overlay
  if feat.values[0] == ColorTextureWidgetFunc.MAP_CANVAS:
    return layer.materialManager.getCanvasImageIndex(feat.values[1])

  if isinstance(feat.values[0], list):   # LAYER
    size = settings.mapSettings.outputSize()
    extent = settings.baseExtent
    return layer.materialManager.getLayerImageIndex(feat.values[0], size.width(), size.height(), extent, feat.values[1])

  return layer.materialManager.getMeshLambertIndex(feat.values[0], feat.values[1], True)


def geometry(settings, layer, feat, geom):
  polygons = []
  zs = []
  for polygon in geom.polygons:
    bnds = []
    zsum = zcount = 0
    for boundary in polygon:
      bnds.append([[pt.x, pt.y] for pt in boundary])
      zsum += sum([pt.z for pt in boundary], -boundary[0].z)
      zcount += len(boundary) - 1
    polygons.append(bnds)
    zs.append(zsum / zcount)

  g = {"polygons": polygons}

  if layer.prop.type_index == 0:  # Extruded
    g["zs"] = zs
    g["h"] = feat.values[2] * settings.mapTo3d().multiplierZ

  else:   # Overlay
    #TODO: mb and ms
    # border
    #if feat.values[2] is not None:
    #  g["mb"] = layer.materialManager.getLineBasicIndex(feat.values[2], feat.values[1])

    # side
    if feat.values[3]:
      #g["ms"] = layer.materialManager.getMeshLambertIndex(feat.values[4], feat.values[1], doubleSide=True)

      # bottom height of side
      g["sb"] = feat.values[5] * settings.mapTo3d().multiplierZ

    # If height mode is relative to DEM, height from DEM. Otherwise from zero altitude.
    # Vertical shift is not considered (will be shifted in JS).
    g["h"] = feat.altitude * settings.mapTo3d().multiplierZ

    polygons = []
    triangles = Triangles()
    for polygon in geom.split_polygons:
      boundary = polygon[0]
      if len(polygon) == 1 and len(boundary) == 4:
        triangles.addTriangle(boundary[0], boundary[2], boundary[1])    # vertex order should be counter-clockwise
      else:
        bnds = [[[pt.x, pt.y] for pt in bnd] for bnd in polygon]
        polygons.append(bnds)

    if triangles.vertices:
      g["triangles"] = {"v": [[pt.x, pt.y] for pt in triangles.vertices], "f": triangles.faces}

    if polygons:
      g["split_polygons"] = polygons

  if geom.centroids:
    g["centroids"] = [[pt.x, pt.y, pt.z] for pt in geom.centroids]

  return g
