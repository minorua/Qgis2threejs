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

from Qgis2threejs.stylewidget import StyleWidget, ColorWidgetFunc, OptionalColorWidgetFunc, ColorTextureWidgetFunc
from Qgis2threejs.geometry import IndexedTriangles2D, IndexedTriangles3D


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
  tr("Extruded"), tr("Overlay"), tr("Triangular Mesh")
  tr("Icon"), tr("JSON model"), tr("COLLADA model")


class ObjectTypeBase:

  experimental = False

  @classmethod
  def displayName(cls):
    return tr(cls.name)

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    pass

  @classmethod
  def layerProperties(cls, settings, layer):
    return {}

  @classmethod
  def material(cls, settings, layer, feat):
    pass

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    pass

  @classmethod
  def defaultValue(cls, mapTo3d):
    return float("{0:.4g}".format(1.0 / mapTo3d.multiplier))

  @classmethod
  def defaultValueZ(cls, mapTo3d):
    return float("{0:.4g}".format(1.0 / mapTo3d.multiplierZ))


class PointTypeBase(ObjectTypeBase):

  geometryType = QgsWkbTypes.PointGeometry


class LineTypeBase(ObjectTypeBase):

  geometryType = QgsWkbTypes.LineGeometry


class PolygonTypeBase(ObjectTypeBase):

  geometryType = QgsWkbTypes.PolygonGeometry


### PointBasicType
class PointBasicTypeBase(PointTypeBase):

  @classmethod
  def material(cls, settings, layer, feat):
    return layer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1])


class SphereType(PointBasicTypeBase):

  name = "Sphere"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Radius", "defaultValue": cls.defaultValue(mapTo3d), "layer": layer})

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    return {"pts": geom.asList(),
            "r": feat.values[2] * settings.mapTo3d().multiplier}


class CylinderType(PointBasicTypeBase):

  name = "Cylinder"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Radius", "defaultValue": cls.defaultValue(mapTo3d), "layer": layer})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Height", "defaultValue": cls.defaultValueZ(mapTo3d), "layer": layer})

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    mapTo3d = settings.mapTo3d()
    r = feat.values[2] * mapTo3d.multiplier
    return {"pts": geom.asList(),
            "r": r,
            "h": feat.values[3] * mapTo3d.multiplierZ}


class ConeType(CylinderType):

  name = "Cone"


class BoxType(PointBasicTypeBase):

  name = "Box"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    val = cls.defaultValue(mapTo3d)
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Width", "defaultValue": val, "layer": layer})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Depth", "defaultValue": val, "layer": layer})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Height", "defaultValue": cls.defaultValueZ(mapTo3d), "layer": layer})

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    mapTo3d = settings.mapTo3d()
    return {"pts": geom.asList(),
            "w": feat.values[2] * mapTo3d.multiplier,
            "d": feat.values[3] * mapTo3d.multiplier,
            "h": feat.values[4] * mapTo3d.multiplierZ}


class DiskType(PointBasicTypeBase):

  name = "Disk"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Radius", "defaultValue": cls.defaultValue(mapTo3d), "layer": layer})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Dip", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": layer})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Dip direction", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": layer})

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
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

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.CHECKBOX, {"name": "Dashed", "defaultValue": False})

  @classmethod
  def material(cls, settings, layer, feat):
    try:
      if feat.values[2]:
        return layer.materialManager.getDashedLineIndex(feat.values[0], feat.values[1])
    except IndexError:    # for backward compatibility (dashed option was added in 2.1)
      pass

    return layer.materialManager.getBasicLineIndex(feat.values[0], feat.values[1])

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    return {"lines": geom.asList()}


class PipeType(LineBasicTypeBase):

  name = "Pipe"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Radius", "defaultValue": cls.defaultValue(mapTo3d), "layer": layer})

  @classmethod
  def material(cls, settings, layer, feat):
    return layer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1])

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    r = feat.values[2] * settings.mapTo3d().multiplier
    return {"lines": geom.asList(),
            "r": r}


class ConeLineType(PipeType):

  name = "Cone"


class BoxLineType(LineBasicTypeBase):

  name = "Box"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    val = cls.defaultValue(mapTo3d)
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Width", "defaultValue": val, "layer": layer})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Height", "defaultValue": val, "layer": layer})

  @classmethod
  def material(cls, settings, layer, feat):
    return layer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1])

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    multiplier = settings.mapTo3d().multiplier
    return {"lines": geom.asList(),
            "w": feat.values[2] * multiplier,
            "h": feat.values[3] * multiplier}


class ProfileType(LineBasicTypeBase):

  name = "Profile"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Other side Z", "layer": layer})

  @classmethod
  def material(cls, settings, layer, feat):
    return layer.materialManager.getFlatMeshMaterialIndex(feat.values[0], feat.values[1], doubleSide=True)

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    return {"lines": geom.asList(),
            "bh": feat.values[2] * settings.mapTo3d().multiplierZ}


### PolygonBasicType
class PolygonBasicTypeBase(PolygonTypeBase):

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    return {"polygons": [[[[pt.x, pt.y] for pt in bnd] for bnd in poly] for poly in geom.polygons],
            "centroids": [[pt.x, pt.y, pt.z] for pt in geom.centroids]}


class ExtrudedType(PolygonBasicTypeBase):

  name = "Extruded"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Height", "defaultValue": cls.defaultValueZ(mapTo3d), "layer": layer})

    opt = {"name": "Border color",
           "itemText": {OptionalColorWidgetFunc.NONE: "(No border)"},
           "defaultItem": ColorWidgetFunc.FEATURE}
    ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

  @classmethod
  def material(cls, settings, layer, feat):
    mtl = {"face": layer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1])}

    # border
    if feat.values[3] is not None:
      mtl["border"] = layer.materialManager.getBasicLineIndex(feat.values[3], feat.values[1])
    return mtl

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    g = PolygonBasicTypeBase.geometry(settings, layer, feat, geom)
    g["h"] = feat.values[2] * settings.mapTo3d().multiplierZ
    return g


class OverlayType(PolygonBasicTypeBase):

  name = "Overlay"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()

    #TODO: [Polygon - Overlay] border
    # opt = {"name": "Border color",
    #        "itemText": {OptionalColorWidgetFunc.NONE: "(No border)"},
    #        "defaultItem": ColorWidgetFunc.FEATURE}
    # ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

  @classmethod
  def material(cls, settings, layer, feat):
    if feat.values[0] == ColorTextureWidgetFunc.MAP_CANVAS:
      return layer.materialManager.getCanvasImageIndex(feat.values[1])

    if isinstance(feat.values[0], list):   # LAYER
      size = settings.mapSettings.outputSize()
      extent = settings.baseExtent
      return layer.materialManager.getLayerImageIndex(feat.values[0], size.width(), size.height(), extent, feat.values[1])

    return layer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1], True)

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    if layer.prop.isHeightRelativeToDEM():
      g = {}

      polygons = []
      triangles = IndexedTriangles2D()
      for polygon in geom.polygons:
        boundary = polygon[0]
        if len(polygon) == 1 and len(boundary) == 4:
          triangles.addTriangle(boundary[0], boundary[2], boundary[1])    # vertex order should be counter-clockwise
        else:
          bnds = [[[pt.x, pt.y, pt.z] for pt in bnd] for bnd in polygon]
          polygons.append(bnds)

      if triangles.vertices:
        g["triangles"] = {"v": [[pt.x, pt.y, pt.z] for pt in triangles.vertices], "f": triangles.faces}

      if polygons:
        g["split_polygons"] = polygons

      if geom.centroids:
        g["centroids"] = [[pt.x, pt.y, pt.z] for pt in geom.centroids]

    else:
      g = PolygonBasicTypeBase.geometry(settings, layer, feat, geom)

    g["h"] = feat.altitude * settings.mapTo3d().multiplierZ

    #TODO: [Polygon - Overlay] border
    # if feat.values[2] is not None:
    #   g["mb"] = layer.materialManager.getBasicLineIndex(feat.values[2], feat.values[1])

    return g


class TriangularMeshType(PolygonBasicTypeBase):

  name = "Triangular Mesh"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    ppage.initStyleWidgets()

  @classmethod
  def material(cls, settings, layer, feat):
    return layer.materialManager.getFlatMeshMaterialIndex(feat.values[0], feat.values[1], True)

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    triangles = IndexedTriangles3D()
    for polygon in geom.polygons:
      boundary = polygon[0]
      triangles.addTriangle(boundary[0], boundary[1], boundary[2])

    v = []
    for pt in triangles.vertices:
      v.extend([pt.x, pt.y, pt.z])

    f = []
    for s in triangles.faces:
      f.extend(s)

    g = {"v": v, "f": f}
    if geom.centroids:
      g["centroids"] = [[pt.x, pt.y, pt.z] for pt in geom.centroids]
    return g


### IconType
class IconType(PointTypeBase):

  name = "Icon"

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer):
    filterString = "Images (*.png *.jpg *.gif *.bmp);;All files (*.*)"

    ppage.initStyleWidgets(color=False)
    ppage.addStyleWidget(StyleWidget.FILEPATH, {"name": "Image file", "layer": layer, "filterString": filterString})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Scale", "defaultValue": 1, "layer": layer})

  @classmethod
  def material(cls, settings, layer, feat):
    image_path = feat.values[1]
    return layer.materialManager.getSpriteIndex(image_path, feat.values[0])

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    return {"pts": geom.asList(),
            "scale": feat.values[2]}


### ModelType
class ModelTypeBase(PointTypeBase):

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer, label, filterString):
    ppage.initStyleWidgets(color=False, opacity=False)
    ppage.addStyleWidget(StyleWidget.FILEPATH, {"name": label, "layer": layer, "filterString": filterString})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Scale", "defaultValue": 1, "layer": layer})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Rotation (x)", "label": "Degrees", "defaultValue": 0, "layer": layer})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Rotation (y)", "label": "Degrees", "defaultValue": 0, "layer": layer})
    ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Rotation (z)", "label": "Degrees", "defaultValue": 0, "layer": layer})

  @classmethod
  def geometry(cls, settings, layer, feat, geom):
    model_path = feat.values[0]
    model_type = cls.name.split(" ")[0]
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


#TODO: [Point - JSON model]
class JSONModelType(ModelTypeBase):

  name = "JSON model"
  experimental = True

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer, label, filterString):
    ModelTypeBase.setupWidgets(ppage, mapTo3d, layer, "JSON file", "JSON files (*.json *.js);;All files (*.*)")


#TODO: [Point - COLLADA model]
class COLLADAModelType(ModelTypeBase):

  name = "COLLADA model"
  experimental = True

  @classmethod
  def setupWidgets(cls, ppage, mapTo3d, layer, label, filterString):
    ModelTypeBase.setupWidgets(ppage, mapTo3d, layer, "COLLADA file", "COLLADA files (*.dae);;All files (*.*)")


### ObjectTypeRegistry
class ObjectTypeRegistry:

  def __init__(self):
    self.objTypes = {
      QgsWkbTypes.PointGeometry: [SphereType, CylinderType, ConeType, BoxType, DiskType, IconType],    # disabled since v.2.0: JSONModelType, COLLADAModelType],
      QgsWkbTypes.LineGeometry: [LineType, PipeType, ConeLineType, BoxLineType, ProfileType],
      QgsWkbTypes.PolygonGeometry: [ExtrudedType, OverlayType, TriangularMeshType]
    }

  def objectTypes(self, geom_type):
    return self.objTypes.get(geom_type, [])

  def objectType(self, geom_type, name):
    for obj_type in self.objectTypes(geom_type):
      if obj_type.name == name:
        return obj_type
    return None
