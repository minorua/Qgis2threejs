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
from qgis.core import QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry, QgsProject, QgsRenderContext, QgsWkbTypes

from .conf import debug_mode
from .datamanager import MaterialManager
from .exportlayer import LayerExporter
from .geometry import Geometry, PointGeometry, LineGeometry, PolygonGeometry, TriangleMesh
from .propertyreader import DEMPropertyReader, VectorPropertyReader
from .qgis2threejstools import logMessage
from .vectorobject import objectTypeRegistry


class VectorLayerExporter(LayerExporter):

  def __init__(self, settings, imageManager, layer, pathRoot=None, urlRoot=None, progress=None):
    LayerExporter.__init__(self, settings, imageManager, layer, pathRoot, urlRoot, progress)

    self.materialManager = MaterialManager()    #TODO: takes imageManager

    self.mapTo3d = settings.mapTo3d()
    self.geomType = self.layer.mapLayer.geometryType()
    self.fidx = None

    self.demSize = None

  def build(self, export_blocks=False):
    mapLayer = self.layer.mapLayer
    if mapLayer is None:
      return

    properties = self.layer.properties
    baseExtent = self.settings.baseExtent
    mapSettings = self.settings.mapSettings
    renderContext = QgsRenderContext.fromMapSettings(mapSettings)

    self.prop = VectorPropertyReader(objectTypeRegistry(), renderContext, mapLayer, properties)
    if self.prop.objType is None:
      logMessage("Object type not found")
      return

    # prepare triangle mesh
    if self.prop.objType.name == "Overlay" and self.prop.isHeightRelativeToDEM():
      # get the grid size of the DEM layer which polygons overlay
      demProp = self.settings.getPropertyReaderByLayerId(properties.get("comboBox_altitudeMode"))
      if demProp:
        self.demSize = demProp.demSize(mapSettings.outputSize())

    layer = VectorLayer(self.settings, mapLayer, self.prop, self.materialManager)
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
    mapLayer.renderer().startRender(renderContext, mapLayer.fields())
    self.features = layer.features(request)
    mapLayer.renderer().stopRender(renderContext)

    # materials
    for feat in self.features:
      #if self.isCancelled:
      #  break

      feat.material = self.prop.objType.material(self.settings, layer, feat)

    gt2str = {
      QgsWkbTypes.PointGeometry: "point",
      QgsWkbTypes.LineGeometry: "line",
      QgsWkbTypes.PolygonGeometry: "polygon"
      }

    # properties
    p = {
      "type": gt2str.get(mapLayer.geometryType()),
      "objType": self.prop.objType.name,
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

    data = {}
    data["materials"] = self.materialManager.buildAll(self.imageManager, base64=self.settings.base64)

    if export_blocks:
      data["blocks"] = [block.build() for block in self.blocks()]

    d = {
      "type": "layer",
      "id": self.layer.jsLayerId,
      "properties": p,
      "data": data
      }

    if debug_mode:
      d["PROPERTIES"] = properties
    return d

  def blocks(self):
    index = 0
    FEATURE_COUNT = 50

    def block(blockIndex, features):
      return FeatureBlockExporter(blockIndex, {
        "type": "block",
        "layer": self.layer.jsLayerId,
        "block": blockIndex,
        "features": features
        }, self.pathRoot, self.urlRoot)

    demProvider = demSize = None
    if self.prop.isHeightRelativeToDEM():
      demProvider = self.settings.demProviderByLayerId(self.layer.properties.get("comboBox_altitudeMode"))

    if self.layer.properties.get("radioButton_zValue"):
      useZM = Geometry.UseZ
    elif self.layer.properties.get("radioButton_mValue"):
      useZM = Geometry.UseM
    else:
      useZM = Geometry.NotUseZM

    feats = []
    for feat in self.features or []:
      geom = feat.geometry(self.mapTo3d, useZM, demProvider, self.clipGeom, self.hasLabel, self.settings.baseExtent, self.demSize)
      if geom is None:
        continue

      f = {}
      f["geom"] = self.prop.objType.geometry(self.settings, self._layer, feat, geom)
      f["mtl"] = feat.material

      if feat.attributes is not None:
        f["prop"] = feat.attributes

      feats.append(f)

      if len(feats) == FEATURE_COUNT:
        yield block(index, feats)
        index += 1
        feats = []

    if len(feats) or index == 0:
      yield block(index, feats)


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

  def __init__(self, layer, qGeom, altitude, propValues, attrs=None):
    self.layerProp = layer.prop
    self.geom = qGeom
    self.geomType = layer.geomType
    self.geomClass = layer.geomType2Class.get(layer.geomType)
    self.altitude = altitude
    self.values = propValues
    self.attributes = attrs

    self.material = -1

  def geometry(self, mapTo3d, useZM=Geometry.NotUseZM, demProvider=None, clipGeom=None, calcCentroid=False, baseExtent=None, demSize=None):
    """calcCentroid: for polygon geometry
       demSize: grid size of the DEM layer which polygons overlay"""
    # z_func: function to get elevation at given point (x, y) on surface
    if demProvider:
      if self.layerProp.objType.name == "Overlay":
        #TODO: [Polygon - Overlay] rotated map support
        center = baseExtent.center()
        half_width, half_height = baseExtent.width() / 2, baseExtent.height() / 2
        xmin, ymin = center.x() - half_width, center.y() - half_height
        xmax, ymax = center.x() + half_width, center.y() + half_height
        xres, yres = baseExtent.width() / (demSize.width() - 1), baseExtent.height() / (demSize.height() - 1)
        tmesh = TriangleMesh(xmin, ymin, xmax, ymax, demSize.width() - 1, demSize.height() - 1)
        z_func = lambda x, y: demProvider.readValueOnTriangles(x, y, xmin, ymin, xres, yres)
      else:
        z_func = lambda x, y: demProvider.readValue(x, y)
    else:
      z_func = lambda x, y: 0

    # transform_func: function to transform the map coordinates to 3d coordinates
    transform_func = lambda x, y, z: mapTo3d.transform(x, y, z + self.altitude)

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
      if self.layerProp.objType.name == "Overlay" and self.layerProp.isHeightRelativeToDEM():
        geom = tmesh.splitPolygon(geom)
        useCentroidHeight = False
      else:
        useCentroidHeight = True
      return self.geomClass.fromQgsGeometry(geom, z_func, transform_func, calcCentroid, useCentroidHeight)

    else:
      return self.geomClass.fromQgsGeometry(geom, z_func, transform_func, useZM=useZM)


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

  def __init__(self, settings, layer, prop, materialManager):
    Layer.__init__(self, settings, layer, prop)
    self.materialManager = materialManager

    self.transform = QgsCoordinateTransform(layer.crs(), settings.crs, QgsProject.instance())
    self.geomType = layer.geometryType()
    self.geomClass = self.geomType2Class.get(self.geomType)

    # attributes
    properties = prop.properties
    self.writeAttrs = properties.get("checkBox_ExportAttrs", False)
    self.fieldNames = None
    self.labelAttrIndex = None

    if self.writeAttrs:
      self.fieldNames = [field.name() for field in layer.fields()]
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
    obj["objType"] = prop.objType.name

    if self.hasLabel():
      widgetValues = properties.get("labelHeightWidget", {})
      obj["l"] = {"i": self.labelAttrIndex,
                  "ht": int(widgetValues.get("comboData", 0)),
                  "v": float(widgetValues.get("editText", 0)) * mapTo3d.multiplierZ}

    # object-type-specific properties
    obj.update(self.prop.objType.layerProperties(self.settings, self))

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
      altitude = prop.altitude()
      propVals = prop.values(f)

      attrs = f.attributes() if self.writeAttrs else None

      # create a feature object
      feat = Feature(self, geom, altitude, propVals, attrs)
      feats.append(feat)

    return feats
