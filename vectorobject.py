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

from Qgis2threejs.stylewidget import StyleWidget, ColorWidgetFunc, HeightWidgetFunc, LabelHeightWidgetFunc, OptionalColorWidgetFunc, ColorTextureWidgetFunc
from Qgis2threejs.geometry import Triangles


_objectTypeRegistry = None

def objectTypeRegistry():
  global _objectTypeRegistry
  if _objectTypeRegistry is None:
    _objectTypeRegistry = ObjectTypeRegistry()
  return _objectTypeRegistry


def tr(source):
  return source


def _():
  tr("Sphere"), tr("Cylinder"), tr("Cone"), tr("Box"), tr("Disk")
  tr("Line"), tr("Pipe"), tr("Profile")
  tr("Extruded"), tr("Overlay")
  tr("Icon"), tr("JSON model"), tr("COLLADA model")


class ObjectTypeBase:

  def __init__(self):
    self.experimental = False
    self.displayName = tr(self.name)

  def setupWidgets(self, ppage, mapTo3d, layer):
    pass

#TODO: setupWidgets -> widgets?
#  def widgets(self, settings, layer):
#    return [const.Color,
#            const.Opacity,
#            {"type": StyleWidget.FIELD_VALUE, "name": "Height", "defaultValue": 0}]

  def layerProperties(self, settings, layer):
    return {}

  def material(self, settings, layer, feat):
    pass

  def geometry(self, settings, layer, feat, geom):
    pass

  def defaultValue(self, mapTo3d):
    return float("{0:.4g}".format(1.0 / mapTo3d.multiplier))

  def defaultValueZ(self, mapTo3d):
    return float("{0:.4g}".format(1.0 / mapTo3d.multiplierZ))


class PointTypeBase(ObjectTypeBase):

  geometryType = QgsWkbTypes.PointGeometry


class LineTypeBase(ObjectTypeBase):

  geometryType = QgsWkbTypes.LineGeometry


class PolygonTypeBase(ObjectTypeBase):

  geometryType = QgsWkbTypes.PolygonGeometry


### PointBasicType
class PointBasicTypeBase(PointTypeBase):

  def material(self, settings, layer, feat):
    return layer.materialManager.getMeshLambertIndex(feat.values[0], feat.values[1])


class SphereType(PointBasicTypeBase):

  name = "Sphere"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": self.defaultValue(mapTo3d), "layer": layer})

  def geometry(self, settings, layer, feat, geom):
    return {"pts": geom.asList(),
            "r": feat.values[2] * settings.mapTo3d().multiplier}


class CylinderType(PointBasicTypeBase):

  name = "Cylinder"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": self.defaultValue(mapTo3d), "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": self.defaultValueZ(mapTo3d), "layer": layer})

  def geometry(self, settings, layer, feat, geom):
    mapTo3d = settings.mapTo3d()
    r = feat.values[2] * mapTo3d.multiplier
    return {"pts": geom.asList(),
            "rt": r, "rb": r,
            "h": feat.values[3] * mapTo3d.multiplierZ,
            "rotateX": 90}


class ConeType(CylinderType):

  name = "Cone"

  def geometry(self, settings, layer, feat, geom):
    mapTo3d = settings.mapTo3d()
    r = feat.values[2] * mapTo3d.multiplier
    return {"pts": geom.asList(),
            "rt": 0, "rb": r,
            "h": feat.values[3] * mapTo3d.multiplierZ,
            "rotateX": 90}


class BoxType(PointBasicTypeBase):

  name = "Box"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    val = self.defaultValue(mapTo3d)
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Width", "defaultValue": val, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Depth", "defaultValue": val, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": self.defaultValueZ(mapTo3d), "layer": layer})

  def geometry(self, settings, layer, feat, geom):
    mapTo3d = settings.mapTo3d()
    return {"pts": geom.asList(),
            "w": feat.values[2] * mapTo3d.multiplier,
            "d": feat.values[3] * mapTo3d.multiplier,
            "h": feat.values[4] * mapTo3d.multiplierZ,
            "rotateX": 90}


class DiskType(PointBasicTypeBase):

  name = "Disk"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": self.defaultValue(mapTo3d), "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Dip", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Dip direction", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": layer})

  def geometry(self, settings, layer, feat, geom):
    dd = feat.values[4]
    # take map rotation into account
    rotation = settings.baseExtent.rotation()
    if rotation:
      dd = (dd + rotation) % 360

    return {"pts": geom.asList(),
            "r": feat.values[2] * settings.mapTo3d().multiplier,
            "d": feat.values[3],
            "dd": dd}


### LineBasicType
class LineBasicTypeBase(LineTypeBase):

  pass


class LineType(LineBasicTypeBase):

  name = "Line"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()

  def material(self, settings, layer, feat):
    return layer.materialManager.getLineBasicIndex(feat.values[0], feat.values[1])

  def geometry(self, settings, layer, feat, geom):
    return {"lines": geom.asList()}


class PipeType(LineBasicTypeBase):

  name = "Pipe"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Radius", "defaultValue": self.defaultValue(mapTo3d), "layer": layer})

  def material(self, settings, layer, feat):
    return layer.materialManager.getMeshLambertIndex(feat.values[0], feat.values[1])

  def geometry(self, settings, layer, feat, geom):
    r = feat.values[2] * settings.mapTo3d().multiplier
    return {"lines": geom.asList(),
            "rt": r,
            "rb": r}


class ConeLineType(PipeType):

  name = "Cone"

  def geometry(self, settings, layer, feat, geom):
    r = feat.values[2] * settings.mapTo3d().multiplier
    return {"lines": geom.asList(),
            "rt": 0,
            "rb": r}


class BoxLineType(LineBasicTypeBase):

  name = "Box"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    val = self.defaultValue(mapTo3d)
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Width", "defaultValue": val, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": val, "layer": layer})

  def material(self, settings, layer, feat):
    return layer.materialManager.getMeshLambertIndex(feat.values[0], feat.values[1])

  def geometry(self, settings, layer, feat, geom):
    multiplier = settings.mapTo3d().multiplier
    return {"lines": geom.asList(),
            "w": feat.values[2] * multiplier,
            "h": feat.values[3] * multiplier}


class ProfileType(LineBasicTypeBase):

  name = "Profile"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.HEIGHT, {"name": "Lower Z", "layer": layer, "defaultItem": HeightWidgetFunc.ABSOLUTE})

  def layerProperties(self, settings, layer):
    cb = layer.prop.properties["styleWidget2"]["comboData"]
    isBRelative = (cb == HeightWidgetFunc.RELATIVE or cb >= HeightWidgetFunc.FIRST_ATTR_REL)
    return {"am": "relative" if layer.prop.isHeightRelativeToDEM() else "absolute", # altitude mode
            "bam": "relative" if isBRelative else "absolute"}                       # altitude mode of bottom

  def material(self, settings, layer, feat):
    return layer.materialManager.getFlatMeshLambertIndex(feat.values[0], feat.values[1], doubleSide=True)

  def geometry(self, settings, layer, feat, geom):
    multiplierZ = settings.mapTo3d().multiplierZ
    if layer.prop.isHeightRelativeToDEM():
      d = {"lines": geom.asList2(),
           "h": feat.altitude * multiplierZ}
    else:
      d = {"lines": geom.asList()}

    d["bh"] = feat.values[2] * multiplierZ
    return d


### PolygonBasicType
class PolygonBasicTypeBase(PolygonTypeBase):

  def geometry(self, settings, layer, feat, geom):
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

    g = {"polygons": polygons, "zs": zs}
    if geom.centroids:
      g["centroids"] = [[pt.x, pt.y, pt.z] for pt in geom.centroids]

    return g


class ExtrudedType(PolygonBasicTypeBase):

  name = "Extruded"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": self.defaultValueZ(mapTo3d), "layer": layer})

    opt = {"name": "Border color",
           "itemText": {OptionalColorWidgetFunc.NONE: "(No border)"},
           "defaultItem": ColorWidgetFunc.FEATURE}
    ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

    ppage.setupLabelHeightWidget([(LabelHeightWidgetFunc.RELATIVE_TO_TOP, "Height from top"),
                                  (LabelHeightWidgetFunc.RELATIVE, "Height from bottom")])

  def material(self, settings, layer, feat):
    mtl = {"face": layer.materialManager.getMeshLambertIndex(feat.values[0], feat.values[1])}

    # border
    if feat.values[3] is not None:
      mtl["border"] = layer.materialManager.getLineBasicIndex(feat.values[3], feat.values[1])
    return mtl

  def geometry(self, settings, layer, feat, geom):
    g = PolygonBasicTypeBase.geometry(self, settings, layer, feat, geom)
    g["h"] = feat.values[2] * settings.mapTo3d().multiplierZ
    return g


class OverlayType(PolygonBasicTypeBase):

  name = "Overlay"

  def setupWidgets(self, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Height", "defaultValue": self.defaultValueZ(mapTo3d), "layer": layer})

    opt = {"name": "Border color",
           "itemText": {OptionalColorWidgetFunc.NONE: "(No border)"},
           "defaultItem": ColorWidgetFunc.FEATURE}
    ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

    ppage.setupLabelHeightWidget([(LabelHeightWidgetFunc.RELATIVE_TO_TOP, "Height from overlay"),
                                  (LabelHeightWidgetFunc.RELATIVE, "Height from DEM")])

  #TODO
  def layerProperties(self, settings, layer):
    prop = layer.prop
    cb = prop.properties["styleWidget5"]["comboData"]
    isSbRelative = (cb == HeightWidgetFunc.RELATIVE or cb >= HeightWidgetFunc.FIRST_ATTR_REL)
    return {"am": "relative" if prop.isHeightRelativeToDEM() else "absolute",   # altitude mode
            "sbm": "relative" if isSbRelative else "absolute"}                  # altitude mode of bottom of side

  def material(self, settings, layer, feat):
    if feat.values[0] == ColorTextureWidgetFunc.MAP_CANVAS:
      return layer.materialManager.getCanvasImageIndex(feat.values[1])

    if isinstance(feat.values[0], list):   # LAYER
      size = settings.mapSettings.outputSize()
      extent = settings.baseExtent
      return layer.materialManager.getLayerImageIndex(feat.values[0], size.width(), size.height(), extent, feat.values[1])

    return layer.materialManager.getMeshLambertIndex(feat.values[0], feat.values[1], True)

  def geometry(self, settings, layer, feat, geom):
    g = PolygonBasicTypeBase.geometry(self, settings, layer, feat, geom)
    del g["zs"]

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

    return g


### IconType
class IconType(PointTypeBase):

  name = "Icon"

  def setupWidgets(self, ppage, mapTo3d, layer):
    filterString = "Images (*.png *.jpg *.gif *.bmp);;All files (*.*)"

    ppage.initStyleWidgets(color=False)
    ppage.addStyleWidget(StyleWidget.FILEPATH, {"name": "Image file", "layer": layer, "filterString": filterString})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Scale", "defaultValue": 1, "layer": layer})

  def material(self, settings, layer, feat):
    image_path = feat.values[1]
    return layer.materialManager.getSpriteIndex(image_path, feat.values[0])

  def geometry(self, settings, layer, feat, geom):
    return {"pts": geom.asList(),
            "scale": feat.values[2]}


### ModelType
class ModelTypeBase(PointTypeBase):

  def setupWidgets(self, ppage, mapTo3d, layer, label, filterString):
    ppage.initStyleWidgets(color=False, opacity=False)
    ppage.addStyleWidget(StyleWidget.FILEPATH, {"name": label, "layer": layer, "filterString": filterString})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Scale", "defaultValue": 1, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Rotation (x)", "label": "Degrees", "defaultValue": 0, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Rotation (y)", "label": "Degrees", "defaultValue": 0, "layer": layer})
    ppage.addStyleWidget(StyleWidget.FIELD_VALUE, {"name": "Rotation (z)", "label": "Degrees", "defaultValue": 0, "layer": layer})

  def geometry(self, settings, layer, feat, geom):
    model_path = feat.values[0]
    model_type = self.name.split(" ")[0]
    index = layer.modelManager.modelIndex(model_path, model_type)

    rz = feat.values[4]
    # take map rotation into account
    rotation = settings.baseExtent.rotation()
    if rotation:
      rz = (rz - rotation) % 360    # map rotation is clockwise

    return {"model_index": index,
            "pts": geom.asList(),
            "rotateX": feat.values[2],
            "rotateY": feat.values[3],
            "rotateZ": rz,
            "scale": feat.values[1] * settings.mapTo3d().multiplier}


class JSONModelType(ModelTypeBase):

  name = "JSON model"

  def setupWidgets(self, ppage, mapTo3d, layer, label, filterString):
    ModelTypeBase.setupWidgets(self, ppage, mapTo3d, layer, "JSON file", "JSON files (*.json *.js);;All files (*.*)")


class COLLADAModelType(ModelTypeBase):

  name = "COLLADA model"

  def setupWidgets(self, ppage, mapTo3d, layer, label, filterString):
    ModelTypeBase.setupWidgets(self, ppage, mapTo3d, layer, "COLLADA file", "COLLADA files (*.dae);;All files (*.*)")


### ObjectTypeRegistry
class ObjectTypeRegistry:

  def __init__(self):
    # instantiate object type classes
    ptClss = [SphereType, CylinderType, ConeType, BoxType, DiskType, IconType, JSONModelType, COLLADAModelType]
    lnClss = [LineType, PipeType, ConeLineType, BoxLineType, ProfileType]
    plClss = [ExtrudedType, OverlayType]
    self.objTypes = {
      QgsWkbTypes.PointGeometry: [cls() for cls in ptClss],
      QgsWkbTypes.LineGeometry: [cls() for cls in lnClss],
      QgsWkbTypes.PolygonGeometry: [cls() for cls in plClss]
    }

  def objectTypes(self, geom_type):
    return self.objTypes.get(geom_type, [])

  def objectType(self, geom_type, name):
    for obj_type in self.objectTypes(geom_type):
      if obj_type.name == name:
        return obj_type
    return None
