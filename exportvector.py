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
from qgis.core import QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry, QgsMapLayer, QgsPoint, QgsProject, QgsRenderContext, QgsWkbTypes
from osgeo import ogr, osr

from .exportlayer import LayerExporter
from .geometry import PointGeometry, LineGeometry, PolygonGeometry, TriangleMesh, dissolvePolygonsOnCanvas
from .propertyreader import DEMPropertyReader, VectorPropertyReader
from .qgis2threejscore import ObjectTreeItem
from . import qgis2threejstools as tools
from .qgis2threejstools import logMessage
from .vectorobject import objectTypeManager


class VectorLayerExporter(LayerExporter):

  def __init__(self, settings, imageManager, progress=None):
    LayerExporter.__init__(self, settings, imageManager, progress)
    self.triMesh = {}

  def build(self, layerId, properties, jsLayerId, visible=True, pathRoot=None, urlRoot=None):
    """if both pathRoot and urlRoot are None, object is built in all_in_dict mode."""

    mapLayer = QgsProject.instance().mapLayer(layerId)
    if mapLayer is None:
      return

    baseExtent = self.settings.baseExtent
    mapSettings = self.settings.mapSettings
    renderContext = QgsRenderContext.fromMapSettings(mapSettings)
    expContext = mapSettings.expressionContext()

    otm = objectTypeManager()
    prop = VectorPropertyReader(otm, renderContext, expContext, mapLayer, properties)
    obj_mod = otm.module(prop.mod_index)
    if obj_mod is None:
      logMessage("Module not found")
      return

    # prepare triangle mesh
    geom_type = mapLayer.geometryType()
    if geom_type == QgsWkbTypes.PolygonGeometry and prop.type_index == 1 and prop.isHeightRelativeToDEM():   # Overlay
      self.progress(None, "Initializing triangle mesh for overlay polygons")
      self.triangleMesh()
      self.progress(None, "Writing vector layer: {0}".format(mapLayer.name()))

    # write layer object
    layer = VectorLayer(self.settings, mapLayer, prop, obj_mod, self.materialManager)

    #if noFeature:
    #  return

    # initialize symbol rendering
    mapLayer.renderer().startRender(renderContext, mapLayer.pendingFields())

    # features to export
    request = QgsFeatureRequest()
    clipGeom = None
    if properties.get("radioButton_IntersectingFeatures", False):
      request.setFilterRect(layer.transform.transformBoundingBox(baseExtent.boundingBox(), QgsCoordinateTransform.ReverseTransform))
      if properties.get("checkBox_Clip"):
        extent = baseExtent.clone().scale(0.999999)   # clip with slightly smaller extent than map canvas extent
        clipGeom = extent.geometry()

    features = []
    for feat in layer.features(request, clipGeom, self.settings.demProvider()):
      #if writer.isCanceled:
      #  break

      geom, mat = obj_mod.write(self.settings, layer, feat)   # writer.writeFeature(layer, feat, obj_mod)
      f = {"geom": geom, "mat": mat}

      if layer.writeAttrs:
        f["prop"] = feat.attributes()

      features.append(f)

    mapLayer.renderer().stopRender(renderContext)

    gt2str = {
      QgsWkbTypes.PointGeometry: "point",
      QgsWkbTypes.LineGeometry: "line",
      QgsWkbTypes.PolygonGeometry: "polygon"
      }

    # properties
    p = {
      "type": gt2str.get(geom_type),
      "objType": prop.type_name,
      "name": mapLayer.name(),
      "queryable": 1,
      "visible": visible
      }

    if layer.writeAttrs:
      p["propertyNames"] = layer.fieldNames

    mapTo3d = self.settings.mapTo3d()
    writeAttrs = properties.get("checkBox_ExportAttrs", False)
    labelAttrIndex = properties.get("comboBox_Label")
    if writeAttrs and labelAttrIndex is not None:
      widgetValues = properties.get("labelHeightWidget", {})
      p["label"] = {"index": labelAttrIndex,
                    "heightType": int(widgetValues.get("comboData", 0)),
                    "height": float(widgetValues.get("editText", 0)) * mapTo3d.multiplierZ}

    # data
    d = {
      "features": features,
      "materials": self.materialManager.build(self.imageManager)
      }

    return {
      "type": "layer",
      "id": jsLayerId,
      "properties": p,
      "data": d,
      "PROPERTIES": properties    # debug
      }

  def triangleMesh(self, dem_width=0, dem_height=0):
    if dem_width == 0 and dem_height == 0:
      prop = DEMPropertyReader(self.settings.get(ObjectTreeItem.ITEM_DEM))
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


class Feature:

  def __init__(self, settings, layer, feat):
    self.settings = settings
    self.layer = layer
    self.feat = feat
    self.geom = None

    self.prop = layer.prop

  def attributes(self):
    return self.feat.attributes()

  def relativeHeight(self):
    return self.prop.relativeHeight(self.feat)

  def propValues(self):
    return self.prop.values(self.feat)


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

  def features(self, request=None, clipGeom=None, demProvider=None):
    mapTo3d = self.settings.mapTo3d()
    baseExtent = self.settings.baseExtent
    baseExtentGeom = baseExtent.geometry()
    rotation = baseExtent.rotation()
    prop = self.prop

    useZ = prop.useZ()
    if useZ:
      srs_from = osr.SpatialReference()
      srs_from.ImportFromProj4(str(self.layer.crs().toProj4()))
      srs_to = osr.SpatialReference()
      srs_to.ImportFromProj4(str(self.settings.crs.toProj4()))

      ogr_transform = osr.CreateCoordinateTransformation(srs_from, srs_to)
      clipGeomWkb = bytes(clipGeom.exportToWkb()) if clipGeom else None
      ogr_clipGeom = ogr.CreateGeometryFromWkb(clipGeomWkb) if clipGeomWkb else None

    else:
      # z_func: function to get elevation at given point (x, y) on surface
      if prop.isHeightRelativeToDEM():
        if self.geomType == QgsWkbTypes.PolygonGeometry and prop.type_index == 1:  # Overlay
          z_func = lambda x, y: 0
        else:
          # get elevation from DEM
          z_func = lambda x, y: demProvider.readValue(x, y)
      else:
        z_func = lambda x, y: 0

    feats = []
    request = request or QgsFeatureRequest()
    for f in self.layer.getFeatures(request):
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

      # create feature
      feat = Feature(self.settings, self, f)

      # transform_func: function to transform the map coordinates to 3d coordinates
      relativeHeight = prop.relativeHeight(f)

      def transform_func(x, y, z):
        return mapTo3d.transform(x, y, z + relativeHeight)

      if useZ:
        ogr_geom = ogr.CreateGeometryFromWkb(bytes(geometry.exportToWkb()))

        # transform geometry from layer CRS to project CRS
        if ogr_geom.Transform(ogr_transform) != 0:
          logMessage("Failed to transform geometry")
          continue

        # clip geometry
        if ogr_clipGeom and self.geomType == QgsWkbTypes.LineGeometry:
          ogr_geom = ogr_geom.Intersection(ogr_clipGeom)
          if ogr_geom is None:
            continue

        # check if geometry is empty
        if ogr_geom.IsEmpty():
          logMessage("empty geometry skipped")
          continue

        feat.geom = self.geomClass.fromOgrGeometry25D(ogr_geom, transform_func)

      else:
        # clip geometry
        if clipGeom and self.geomType in [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry]:
          geom = geom.intersection(clipGeom)
          if geom is None:
            continue

        # skip if geometry is empty or null
        if geom.isEmpty() or geom.isNull():
          logMessage("empty/null geometry skipped")
          continue

        if self.geomType == QgsWkbTypes.PolygonGeometry:
          feat.geom = self.geomClass.fromQgsGeometry(geom, z_func, transform_func, self.hasLabel())
          if prop.type_index == 1 and prop.isHeightRelativeToDEM():   # Overlay and relative to DEM
            pass
            #TODO:
            #feat.geom.splitPolygon(self.writer.triangleMesh())

        else:
          feat.geom = self.geomClass.fromQgsGeometry(geom, z_func, transform_func)

      if feat.geom is None:
        continue

      #yield feat
      feats.append(feat)

    return feats
    # returns a list, not a iterator
    # QGIS 3 errors
    # SystemError: <built-in function delete_SpatialReference> returned a result with an error set
    # SystemError: <built-in function delete_CoordinateTransformation> returned a result with an error set
