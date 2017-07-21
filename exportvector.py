# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
        begin                : 2014-01-16
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
import json
from osgeo import ogr, osr
from qgis.core import QgsCoordinateTransform, QgsExpressionContext, QgsExpressionContextUtils, QgsFeatureRequest, QgsGeometry, QgsMapLayer, QgsPoint, QgsProject, QgsRenderContext, QgsWkbTypes

from .datamanager import MaterialManager
from .exportlayer import LayerExporter
from .geometry import PointGeometry, LineGeometry, PolygonGeometry, TriangleMesh, dissolvePolygonsOnCanvas
from .propertyreader import DEMPropertyReader, VectorPropertyReader
from .qgis2threejscore import ObjectTreeItem
from . import qgis2threejstools as tools
from .qgis2threejstools import logMessage
from .vectorobject import objectTypeManager


class VectorLayerExporter(LayerExporter):

  def __init__(self, settings, imageManager, layer, pathRoot=None, urlRoot=None, progress=None):
    LayerExporter.__init__(self, settings, imageManager, layer, pathRoot, urlRoot, progress)

    self.materialManager = MaterialManager()    #TODO: takes imageManager
    self.triMesh = {}

    self.mapTo3d = settings.mapTo3d()
    self.geomType = self.layer.mapLayer.geometryType()
    self.fidx = None

  def build(self, export_blocks=False):
    mapLayer = self.layer.mapLayer
    if mapLayer is None:
      return

    properties = self.layer.properties
    baseExtent = self.settings.baseExtent
    mapSettings = self.settings.mapSettings
    renderContext = QgsRenderContext.fromMapSettings(mapSettings)

    otm = objectTypeManager()
    self.prop = VectorPropertyReader(otm, renderContext, mapLayer, properties)
    self.obj_mod = otm.module(self.prop.mod_index)
    if self.obj_mod is None:
      logMessage("Module not found")
      return

    # prepare triangle mesh
    geom_type = mapLayer.geometryType()
    if geom_type == QgsWkbTypes.PolygonGeometry and self.prop.type_index == 1 and self.prop.isHeightRelativeToDEM():   # Overlay
      self.progress(None, "Initializing triangle mesh for overlay polygons")
      self.triangleMesh()
      self.progress(None, "Writing vector layer: {0}".format(mapLayer.name()))

    layer = VectorLayer(self.settings, mapLayer, self.prop, self.obj_mod, self.materialManager)
    self._layer = layer

    #if noFeature:
    #  return

    self.hasLabel = layer.hasLabel()
    self.clipGeom = None

    # feature request
    request = QgsFeatureRequest()
    if properties.get("radioButton_IntersectingFeatures", False):
      request.setFilterRect(layer.transform.transformBoundingBox(baseExtent.boundingBox(), QgsCoordinateTransform.ReverseTransform))

      # geometry for clipping
      if properties.get("checkBox_Clip"):
        extent = baseExtent.clone().scale(0.999999)   # clip with slightly smaller extent than map canvas extent
        self.clipGeom = extent.geometry()

    # initialize symbol rendering, and then get features (geometry, attributes, color, etc.)
    mapLayer.renderer().startRender(renderContext, mapLayer.pendingFields())
    self.features = layer.features(request)
    mapLayer.renderer().stopRender(renderContext)

    # materials
    for feat in self.features:
      #if writer.isCanceled:
      #  break

      feat.material = self.obj_mod.material(self.settings, layer, feat)

    gt2str = {
      QgsWkbTypes.PointGeometry: "point",
      QgsWkbTypes.LineGeometry: "line",
      QgsWkbTypes.PolygonGeometry: "polygon"
      }

    # properties
    p = {
      "type": gt2str.get(geom_type),
      "objType": self.prop.type_name,
      "name": self.layer.name,
      "queryable": 1,
      "visible": self.layer.visible
      }

    if layer.writeAttrs:
      p["propertyNames"] = layer.fieldNames

    writeAttrs = properties.get("checkBox_ExportAttrs", False)
    labelAttrIndex = properties.get("comboBox_Label")
    if writeAttrs and labelAttrIndex is not None:
      widgetValues = properties.get("labelHeightWidget", {})
      p["label"] = {"index": labelAttrIndex,
                    "heightType": int(widgetValues.get("comboData", 0)),
                    "height": float(widgetValues.get("editText", 0)) * self.mapTo3d.multiplierZ}

    d = {}
    d["materials"] = self.materialManager.buildAll(self.imageManager)

    if export_blocks:
      d["blocks"] = [block.build() for block in self.blocks()]

    return {
      "type": "layer",
      "id": self.layer.jsLayerId,
      "properties": p,
      "data": d,
      "PROPERTIES": properties    # debug
      }

  def blocks(self):
    index = 0
    FEATURE_COUNT = 50    #TODO: VERTEX_COUNT

    def block(blockIndex, features):
      return FeatureBlockExporter(blockIndex, {
        "type": "block",
        "layer": self.layer.jsLayerId,
        "block": blockIndex,
        "features": features
        }, self.pathRoot, self.urlRoot)

    demProvider = None
    if self.prop.isHeightRelativeToDEM():
      if self.layer.mapLayer != QgsWkbTypes.PolygonGeometry or self.prop.type_index != 1:  # Overlay
        demProvider = self.settings.demProviderByLayerId(self.layer.properties.get("comboBox_zDEMLayer"))

    feats = []
    for feat in self.features or []:
      geom = feat.geometry(self.mapTo3d, demProvider, self.clipGeom, self.hasLabel)
      if geom is None:
        continue

      f = {}
      f["geom"] = self.obj_mod.geometry(self.settings, self._layer, feat, geom)
      f["mat"] = feat.material

      if feat.attributes is not None:
        f["prop"] = feat.attributes

      feats.append(f)

      if len(feats) == FEATURE_COUNT:
        yield block(index, feats)
        index += 1
        feats = []

    if len(feats) or index == 0:
      yield block(index, feats)

  def triangleMesh(self, dem_width=0, dem_height=0):
    if dem_width == 0 and dem_height == 0:
      #TODO:
      prop = DEMPropertyReader(layerId, self.settings.get(ObjectTreeItem.ITEM_DEM))
      dem_size = prop.demSize(self.settings.mapSettings.outputSize())
      dem_width = dem_size.width()
      dem_height = dem_size.height()

    key = "{0}x{1}".format(dem_width, dem_height)
    if key not in self.triMesh:
      mapTo3d = self.settings.mapTo3d()
      hw = 0.5 * mapTo3d.planeWidth
      hh = 0.5 * mapTo3d.planeHeight
      self.triMesh[key] = TriangleMesh(-hw, -hh, hw, hh, dem_width - 1, dem_height - 1)
    return self.triMesh[key]


class FeatureBlockExporter:
  
  def __init__(self, blockIndex, data, pathRoot=None, urlRoot=None):
    self.blockIndex = blockIndex
    self.data = data
    self.pathRoot = pathRoot
    self.urlRoot = urlRoot

  def build(self):
    if self.pathRoot is not None:
      with open(self.pathRoot + "_GEOM{0}.json".format(self.blockIndex), "w", encoding="UTF-8") as f:
        json.dump(self.data, f, ensure_ascii=False, indent=1)

      url = self.urlRoot + "_GEOM{0}.json".format(self.blockIndex)
      return {"url": url}

    else:
      return self.data

class Feature:

  def __init__(self, layer, qGeom, height, propValues, attrs=None):
    self.layerProp = layer.prop
    self.geom = qGeom
    self.geomType = layer.geomType
    self.geomClass = layer.geomType2Class.get(layer.geomType)
    self.relativeHeight = height
    self.values = propValues
    self.attributes = attrs

    self.material = -1

  def geometry(self, mapTo3d, demProvider=None, clipGeom=None, calcCentroid=False):
    """calcCentroid: for polygon geometry"""
    # z_func: function to get elevation at given point (x, y) on surface
    if demProvider:
      z_func = lambda x, y: demProvider.readValue(x, y)
    else:
      z_func = lambda x, y: 0

    # transform_func: function to transform the map coordinates to 3d coordinates
    transform_func = lambda x, y, z: mapTo3d.transform(x, y, z + self.relativeHeight)

    #if useZ and False:    #TODO: use QGIS API
      # ogr_geom = ogr.CreateGeometryFromWkb(bytes(geometry.exportToWkb()))
      # ...
      # feat.geom = self.geomClass.fromOgrGeometry25D(ogr_geom, transform_func)

    geom = self.geom
    # clip geometry
    if clipGeom and self.geomType in [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry]:
      geom = geom.intersection(clipGeom)
      if geom is None:
        return None

    # skip if geometry is empty or null
    if geom.isEmpty() or geom.isNull():
      logMessage("empty/null geometry skipped")
      return None

    if self.geomType == QgsWkbTypes.PolygonGeometry:
      geom = self.geomClass.fromQgsGeometry(geom, z_func, transform_func, calcCentroid)
      if self.layerProp.type_index == 1 and self.layerProp.isHeightRelativeToDEM():   # Overlay and relative to DEM
        pass
        #TODO:
        #feat.geom.splitPolygon(self.writer.triangleMesh())
      return geom

    else:
      return self.geomClass.fromQgsGeometry(geom, z_func, transform_func)


class Layer:

  def __init__(self, settings, layer, prop):
    self.settings = settings
    self.layer = layer
    self.prop = prop

    self.name = layer.name() if layer else "no title"

  def layerObject(self):
    return {"q": 1,              #queryable
            "name": self.name}


class VectorLayer(Layer):

  geomType2Class = {QgsWkbTypes.PointGeometry: PointGeometry, QgsWkbTypes.LineGeometry: LineGeometry, QgsWkbTypes.PolygonGeometry: PolygonGeometry}

  def __init__(self, settings, layer, prop, obj_mod, materialManager):
    Layer.__init__(self, settings, layer, prop)
    self.obj_mod = obj_mod
    self.materialManager = materialManager

    self.transform = QgsCoordinateTransform(layer.crs(), settings.crs)
    self.geomType = layer.geometryType()
    self.geomClass = self.geomType2Class.get(self.geomType)

    # attributes
    properties = prop.properties
    self.writeAttrs = properties.get("checkBox_ExportAttrs", False)
    self.fieldNames = None
    self.labelAttrIndex = None

    if self.writeAttrs:
      self.fieldNames = [field.name() for field in layer.pendingFields()]
      self.labelAttrIndex = properties.get("comboBox_Label", None)

  def hasLabel(self):
    return bool(self.labelAttrIndex is not None)

  def layerObject(self):
    """layer properties"""
    mapTo3d = self.settings.mapTo3d()
    prop = self.prop
    properties = prop.properties

    obj = Layer.layerObject(self)
    obj["type"] = {QgsWkbTypes.PointGeometry: "point", QgsWkbTypes.LineGeometry: "line", QgsWkbTypes.PolygonGeometry: "polygon"}.get(self.geomType, "")
    obj["objType"] = prop.type_name

    if self.hasLabel():
      widgetValues = properties.get("labelHeightWidget", {})
      obj["l"] = {"i": self.labelAttrIndex,
                  "ht": int(widgetValues.get("comboData", 0)),
                  "v": float(widgetValues.get("editText", 0)) * mapTo3d.multiplierZ}

    # object-type-specific properties
    obj.update(self.obj_mod.layerProperties(self.settings, self))

    return obj

  def features(self, request=None):
    baseExtent = self.settings.baseExtent
    baseExtentGeom = baseExtent.geometry()
    rotation = baseExtent.rotation()
    prop = self.prop

    useZ = prop.useZ()

    feats = []
    for f in self.layer.getFeatures(request or QgsFeatureRequest()):
      geometry = f.geometry()
      if geometry is None:
        logMessage("null geometry skipped")
        continue

      # coordinate transformation - layer crs to project crs
      geom = QgsGeometry(geometry)
      if geom.transform(self.transform) != 0:
        logMessage("Failed to transform geometry")
        continue

      # check if geometry intersects with the base extent (rotated rect)
      if rotation and not baseExtentGeom.intersects(geom):
        continue

      # set feature to expression context
      prop.setContextFeature(f)

      # evaluate expression
      height = prop.relativeHeight()
      propVals = prop.values(f)      # TODO: divide into geomProperties, styleProperties

      attrs = f.attributes() if self.writeAttrs else None

      # create a feature object
      feat = Feature(self, geom, height, propVals, attrs)
      feats.append(feat)

    return feats
