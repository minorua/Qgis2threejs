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
from qgis.core import QGis, QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry, QgsMapLayer, QgsMapRenderer, QgsMapLayerRegistry, QgsPoint

try:
  from osgeo import ogr, osr
except ImportError:
  import ogr
  import osr

from datamanager import ImageManager, ModelManager, MaterialManager
from demblock import DEMBlock, DEMBlocks
from geometry import PointGeometry, LineGeometry, PolygonGeometry, TriangleMesh, dissolvePolygonsOnCanvas
from propertyreader import DEMPropertyReader, VectorPropertyReader
from qgis2threejscore import ObjectTreeItem, GDALDEMProvider
from qgis2threejstools import pyobj2js, logMessage
from quadtree import DEMQuadList
from rotatedrect import RotatedRect


class ThreejsJSWriter:

  # device: an instance of a subclass of QIODevice (QFile, QBuffer, etc.) or a file object
  def __init__(self, device, settings, objectTypeManager):
    self.setDevice(device)
    self.settings = settings
    self.demProvider = settings.demProvider()
    self.objectTypeManager = objectTypeManager

    self.layerCount = 0
    self.currentLayerIndex = 0
    self.currentFeatureIndex = -1
    self.attrs = []
    self.imageManager = ImageManager(settings)
    self.modelManager = ModelManager()
    self.triMesh = {}

  def setDevice(self, device):
    self.device = device
    self.write = device.write if device else None

  def writeProject(self):
    # write project information
    self.write(u"// Qgis2threejs Project\n")
    settings = self.settings
    extent = self.settings.baseExtent
    rect = extent.unrotatedRect()
    mapTo3d = self.settings.mapTo3d()
    wgs84Center = self.settings.wgs84Center()

    args = {"title": settings.title,
            "crs": unicode(settings.crs.authid()),
            "proj": settings.crs.toProj4(),
            "baseExtent": [rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()],
            "rotation": extent.rotation(),
            "width": mapTo3d.planeWidth,
            "zExaggeration": mapTo3d.verticalExaggeration,
            "zShift": mapTo3d.verticalShift,
            "wgs84Center": {"lat": wgs84Center.y(), "lon": wgs84Center.x()}}

    self.write(u"project = new Q3D.Project({0});\n".format(pyobj2js(args)))

  def writeLayer(self, obj, fieldNames=None):
    #TODO: DEMLayerWriter/VectorLayerWriter (subclasses of LayerWriter)
    self.currentLayerIndex = self.layerCount
    type2classprefix = {"dem": "DEM", "point": "Point", "line": "Line", "polygon": "Polygon"}
    self.write(u"\n// Layer {0}\n".format(self.currentLayerIndex))
    self.write(u"lyr = project.addLayer(new Q3D.{0}Layer({1}));\n".format(type2classprefix[obj["type"]], pyobj2js(obj)))
    # del obj["type"]

    if fieldNames is not None:
      self.write(u"lyr.a = {0};\n".format(pyobj2js(fieldNames)))
    self.layerCount += 1
    self.currentFeatureIndex = -1
    self.attrs = []
    return self.currentLayerIndex

  #TODO: move to VectorLayerWriter
  def writeFeature(self, f):
    self.currentFeatureIndex += 1
    self.write(u"lyr.f[{0}] = {1};\n".format(self.currentFeatureIndex, pyobj2js(f)))

  def addAttributes(self, attrs):
    self.attrs.append(attrs)

  def writeAttributes(self):
    for index, attrs in enumerate(self.attrs):
      self.write(u"lyr.f[{0}].a = {1};\n".format(index, pyobj2js(attrs, True)))

  def writeMaterials(self, materialManager):
    materialManager.write(self, self.imageManager)

  def writeImages(self):
    self.imageManager.write(self)

  def writeModelData(self):
    self.modelManager.write(self)

  def filesToCopy(self):
    # three.js library
    files = [{"dirs": ["js/threejs"]}]

    #TODO: if not export_mode:
    # controls
    files.append({"files": ["js/threejs/controls/" + self.settings.controls], "dest": "threejs"})

    # template specific libraries (files)
    config = self.settings.templateConfig()

    for f in config.get("files", "").strip().split(","):
      p = f.split(">")
      fs = {"files": [p[0]]}
      if len(p) > 1:
        fs["dest"] = p[1]
      files.append(fs)

    for d in config.get("dirs", "").strip().split(","):
      p = d.split(">")
      ds = {"dirs": [p[0]], "subdirs": True}
      if len(p) > 1:
        ds["dest"] = p[1]
      files.append(ds)

    # proj4js
    if self.settings.coordsInWGS84:
      files.append({"dirs": ["js/proj4js"]})

    # model importer
    files += self.modelManager.filesToCopy()

    return files

  def scripts(self):
    files = self.modelManager.scripts()

    # proj4.js
    if self.settings.coordsInWGS84:    # display coordinates in latitude and longitude
      files.append("proj4js/proj4.js")

    # data files
    filetitle = self.settings.htmlfiletitle

    #if self.multiple_files:
    #  files += map(lambda x: "%s_%s.js" % (filetitle, x), range(self.jsfile_count))
    #else:
    files.append("%s.js" % filetitle)

    return map(lambda fn: '<script src="./%s"></script>' % fn, files)

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

  def log(self, message):
    logMessage(message)


def writeSimpleDEM(writer, properties, progress=None):
  settings = writer.settings
  mapTo3d = settings.mapTo3d()
  progress = progress or dummyProgress

  prop = DEMPropertyReader(properties)

  # DEM provider
  provider = settings.demProviderByLayerId(prop.layerId)
  if isinstance(provider, GDALDEMProvider):
    demLayer = QgsMapLayerRegistry.instance().mapLayer(prop.layerId)
    layerName = demLayer.name()
  else:
    demLayer = None
    layerName = provider.name()

  # layer
  layer = DEMLayer(writer, demLayer, prop)
  lyr = layer.layerObject()
  lyr.update({"name": layerName})
  writer.writeLayer(lyr)

  # material option
  texture_scale = properties.get("comboBox_TextureSize", 100) / 100
  transparency = properties.get("spinBox_demtransp", 0)
  transp_background = properties.get("checkBox_TransparentBackground", False)

  # display type
  canvas_size = settings.mapSettings.outputSize()
  if properties.get("radioButton_MapCanvas", False):
    if texture_scale == 1:
      mat = layer.materialManager.getCanvasImageIndex(transparency, transp_background)
    else:
      mat = layer.materialManager.getMapImageIndex(canvas_size.width() * texture_scale, canvas_size.height() * texture_scale, settings.baseExtent, transparency, transp_background)

  elif properties.get("radioButton_LayerImage", False):
    layerids = properties.get("layerImageIds", [])
    mat = layer.materialManager.getLayerImageIndex(layerids, canvas_size.width() * texture_scale, canvas_size.height() * texture_scale, settings.baseExtent, transparency, transp_background)

  elif properties.get("radioButton_ImageFile", False):
    filepath = properties.get("lineEdit_ImageFile", "")
    mat = layer.materialManager.getImageFileIndex(filepath, transparency, transp_background, True)

  else:   #.get("radioButton_SolidColor", False)
    mat = layer.materialManager.getMeshLambertIndex(properties.get("lineEdit_Color", ""), transparency, True)

  #elif properties.get("radioButton_Wireframe", False):
  #  block["m"] = layer.materialManager.getWireframeIndex(properties["lineEdit_Color"], transparency)

  # get DEM values
  dem_size = prop.demSize(settings.mapSettings.outputSize())
  dem_width, dem_height = dem_size.width(), dem_size.height()
  dem_values = provider.read(dem_width, dem_height, settings.baseExtent)

  # DEM block
  block = DEMBlock(dem_width, dem_height, dem_values, mapTo3d.planeWidth, mapTo3d.planeHeight, 0, 0)
  block.zShift(mapTo3d.verticalShift)
  block.zScale(mapTo3d.multiplierZ)
  block.set("m", mat)

  surroundings = properties.get("checkBox_Surroundings", False) if prop.layerId else False
  if surroundings:
    blocks = DEMBlocks()
    blocks.appendBlock(block)
    blocks.appendBlocks(surroundingDEMBlocks(writer, layer, provider, properties, progress))
    blocks.processEdges()
    blocks.write(writer)

    writer.write("lyr.stats = {0};\n".format(pyobj2js(blocks.stats())))

  else:
    # clipping
    clip_option = properties.get("checkBox_Clip", False)
    if clip_option:
      clip_layerId = properties.get("comboBox_ClipLayer")
      clip_layer = QgsMapLayerRegistry.instance().mapLayer(clip_layerId) if clip_layerId else None
      if clip_layer:
        block.setClipGeometry(dissolvePolygonsOnCanvas(writer, clip_layer))

    # sides and bottom
    if properties.get("checkBox_Sides", False):
      block.set("sides", True)

    # frame
    if properties.get("checkBox_Frame", False) and not clip_option:
      block.set("frame", True)

    block.write(writer)

    writer.write("lyr.stats = {0};\n".format(pyobj2js(block.orig_stats)))

  # materials
  writer.writeMaterials(layer.materialManager)


def surroundingDEMBlocks(writer, layer, provider, properties, progress=None):
  settings = writer.settings
  canvas_size = settings.mapSettings.outputSize()
  mapTo3d = settings.mapTo3d()
  baseExtent = settings.baseExtent
  progress = progress or dummyProgress

  # options
  size = properties["spinBox_Size"]
  roughening = properties["spinBox_Roughening"]
  texture_scale = properties.get("comboBox_TextureSize", 100) / 100
  transparency = properties.get("spinBox_demtransp", 0)
  transp_background = properties.get("checkBox_TransparentBackground", False)

  prop = DEMPropertyReader(properties)
  dem_size = prop.demSize(canvas_size)
  dem_width = (dem_size.width() - 1) / roughening + 1
  dem_height = (dem_size.height() - 1) / roughening + 1

  # texture size
  image_width = canvas_size.width() * texture_scale
  image_height = canvas_size.height() * texture_scale

  center = baseExtent.center()
  rotation = baseExtent.rotation()

  blocks = []
  size2 = size * size
  for i in range(size2):
    progress(20 * i / size2 + 10)
    if i == (size2 - 1) / 2:    # center (map canvas)
      continue

    # block extent
    sx = i % size - (size - 1) / 2
    sy = i / size - (size - 1) / 2
    block_center = QgsPoint(center.x() + sx * baseExtent.width(), center.y() + sy * baseExtent.height())
    extent = RotatedRect(block_center, baseExtent.width(), baseExtent.height()).rotate(rotation, center)

    # display type
    if properties.get("radioButton_MapCanvas", False):
      mat = layer.materialManager.getMapImageIndex(image_width, image_height, extent, transparency, transp_background)

    elif properties.get("radioButton_LayerImage", False):
      layerids = properties.get("layerImageIds", [])
      mat = layer.materialManager.getLayerImageIndex(layerids, image_width, image_height, extent, transparency, transp_background)

    else:     #.get("radioButton_SolidColor", False)
      mat = layer.materialManager.getMeshLambertIndex(properties.get("lineEdit_Color", ""), transparency, True)

    # DEM block
    dem_values = provider.read(dem_width, dem_height, extent)
    planeWidth, planeHeight = mapTo3d.planeWidth, mapTo3d.planeHeight
    offsetX, offsetY = planeWidth * sx, planeHeight * sy

    block = DEMBlock(dem_width, dem_height, dem_values, planeWidth, planeHeight, offsetX, offsetY)
    block.zShift(mapTo3d.verticalShift)
    block.zScale(mapTo3d.multiplierZ)
    block.set("m", mat)

    blocks.append(block)

  return blocks


def writeMultiResDEM(writer, properties, progress=None):
  settings = writer.settings
  mapSettings = settings.mapSettings
  mapTo3d = settings.mapTo3d()
  baseExtent = settings.baseExtent
  progress = progress or dummyProgress

  prop = DEMPropertyReader(properties)

  # DEM provider
  provider = settings.demProviderByLayerId(prop.layerId)
  if isinstance(provider, GDALDEMProvider):
    demLayer = QgsMapLayerRegistry.instance().mapLayer(prop.layerId)
    layerName = demLayer.name()
  else:
    demLayer = None
    layerName = provider.name()

  # layer
  layer = DEMLayer(writer, demLayer, prop)
  lyr = layer.layerObject()
  lyr.update({"name": layerName})
  writer.writeLayer(lyr)

  # quad tree
  quadtree = settings.quadtree()
  if quadtree is None:
    return

  # (currently) dem size is 2 ^ quadtree.height * a + 1, where a is larger integer than 0
  # with smooth resolution change, this is not necessary
  dem_width = dem_height = max(64, 2 ** quadtree.height) + 1

  # material options
  texture_scale = properties.get("comboBox_TextureSize", 100) / 100
  transparency = properties.get("spinBox_demtransp", 0)
  transp_background = properties.get("checkBox_TransparentBackground", False)
  layerImageIds = properties.get("layerImageIds", [])

  def materialIndex(extent, image_width, image_height):
    # display type
    if properties.get("radioButton_MapCanvas", False):
      return layer.materialManager.getMapImageIndex(image_width, image_height, extent, transparency, transp_background)

    elif properties.get("radioButton_LayerImage", False):
      return layer.materialManager.getLayerImageIndex(layerImageIds, image_width, image_height, extent, transparency, transp_background)

    else:   #.get("radioButton_SolidColor", False)
      return layer.materialManager.getMeshLambertIndex(properties.get("lineEdit_Color", ""), transparency, True)

  blocks = DEMBlocks()

  def addDEMBlock(quad_rect, dem_width, dem_height, dem_values, image_width, image_height):
    planeWidth = quad_rect.width() * mapTo3d.planeWidth
    planeHeight = quad_rect.height() * mapTo3d.planeHeight
    extent = baseExtent.subrectangle(quad_rect)
    npt = baseExtent.normalizePoint(extent.center().x(), extent.center().y())
    offsetX = (npt.x() - 0.5) * mapTo3d.planeWidth
    offsetY = (npt.y() - 0.5) * mapTo3d.planeHeight

    block = DEMBlock(dem_width, dem_height, dem_values, planeWidth, planeHeight, offsetX, offsetY)
    #block.zShift(mapTo3d.verticalShift)
    #block.zScale(mapTo3d.multiplierZ)
    block.set("m", materialIndex(extent, image_width, image_height))

    blocks.appendBlock(block)

  # image size
  canvas_size = mapSettings.outputSize()
  image_width = canvas_size.width() * texture_scale
  image_height = canvas_size.height() * texture_scale

  quads = quadtree.quads()
  unites_center = True
  centerQuads = DEMQuadList(dem_width, dem_height)
  stats = None
  for i, quad in enumerate(quads):
    progress(15 * i / len(quads) + 5)

    # block extent
    extent = baseExtent.subrectangle(quad.rect)

    # warp dem
    dem_values = provider.read(dem_width, dem_height, extent)

    if stats is None:
      stats = {"max": max(dem_values), "min": min(dem_values)}
    else:
      stats["max"] = max(max(dem_values), stats["max"])
      stats["min"] = min(min(dem_values), stats["min"])

    # shift and scale
    if mapTo3d.verticalShift != 0:
      dem_values = map(lambda x: x + mapTo3d.verticalShift, dem_values)
    if mapTo3d.multiplierZ != 1:
      dem_values = map(lambda x: x * mapTo3d.multiplierZ, dem_values)

    quad.setData(dem_width, dem_height, dem_values)

  # process edges to eliminate opening between blocks
  quadtree.processEdges()

  for i, quad in enumerate(quads):
    progress(15 * i / len(quads) + 20)

    if unites_center and quad.height == quadtree.height:
      centerQuads.addQuad(quad)
    else:
      addDEMBlock(quad.rect, quad.dem_width, quad.dem_height, quad.dem_values, image_width, image_height)

  if unites_center:
    dem_width = (dem_width - 1) * centerQuads.width() + 1
    dem_height = (dem_height - 1) * centerQuads.height() + 1
    dem_values = centerQuads.unitedDEM()

    image_width *= centerQuads.width()
    image_height *= centerQuads.height()

    addDEMBlock(centerQuads.rect(), dem_width, dem_height, dem_values, image_width, image_height)

  blocks.write(writer, separated=True)

  writer.write("lyr.stats = {0};\n".format(pyobj2js(stats)))
  writer.writeMaterials(layer.materialManager)


class Feature:

  def __init__(self, writer, layer, feat):
    self.writer = writer
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

  def __init__(self, writer, layer, prop):
    self.writer = writer
    self.layer = layer
    self.prop = prop

    self.materialManager = MaterialManager()

  def layerObject(self):
    obj = {"q": 1}  #queryable
    if self.layer:
      obj["name"] = self.layer.name()
    return obj


class DEMLayer(Layer):

  def layerObject(self):
    obj = Layer.layerObject(self)
    obj["type"] = "dem"

    properties = self.prop.properties
    # shading (whether normals are computed or not)
    if properties.get("checkBox_Shading", True):
      obj["shading"] = True

    return obj


class VectorLayer(Layer):

  geomType2Class = {QGis.Point: PointGeometry, QGis.Line: LineGeometry, QGis.Polygon: PolygonGeometry}

  def __init__(self, writer, layer, prop, obj_mod):
    Layer.__init__(self, writer, layer, prop)
    self.obj_mod = obj_mod

    self.transform = QgsCoordinateTransform(layer.crs(), writer.settings.crs)
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
    mapTo3d = self.writer.settings.mapTo3d()
    prop = self.prop
    properties = prop.properties

    obj = Layer.layerObject(self)
    obj["type"] = {QGis.Point: "point", QGis.Line: "line", QGis.Polygon: "polygon"}.get(self.geomType, "")
    obj["objType"] = prop.type_name

    if self.hasLabel():
      widgetValues = properties.get("labelHeightWidget", {})
      obj["l"] = {"i": self.labelAttrIndex,
                  "ht": int(widgetValues.get("comboData", 0)),
                  "v": float(widgetValues.get("editText", 0)) * mapTo3d.multiplierZ}

    # object-type-specific properties
    obj.update(self.obj_mod.layerProperties(self.writer, self))

    return obj

  def features(self, request=None, clipGeom=None):
    settings = self.writer.settings
    mapTo3d = settings.mapTo3d()
    baseExtent = settings.baseExtent
    baseExtentGeom = baseExtent.geometry()
    rotation = baseExtent.rotation()
    prop = self.prop

    useZ = prop.useZ()
    if useZ:
      srs_from = osr.SpatialReference()
      srs_from.ImportFromProj4(str(self.layer.crs().toProj4()))
      srs_to = osr.SpatialReference()
      srs_to.ImportFromProj4(str(self.writer.settings.crs.toProj4()))

      ogr_transform = osr.CreateCoordinateTransformation(srs_from, srs_to)
      clipGeomWkb = clipGeom.asWkb() if clipGeom else None
      ogr_clipGeom = ogr.CreateGeometryFromWkb(clipGeomWkb) if clipGeomWkb else None

    else:
      # z_func: function to get elevation at given point (x, y) on surface
      if prop.isHeightRelativeToDEM():
        if self.geomType == QGis.Polygon and prop.type_index == 1:  # Overlay
          z_func = lambda x, y: 0
        else:
          # get elevation from DEM
          z_func = lambda x, y: self.writer.demProvider.readValue(x, y)
      else:
        z_func = lambda x, y: 0

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
      feat = Feature(self.writer, self, f)

      # transform_func: function to transform the map coordinates to 3d coordinates
      relativeHeight = prop.relativeHeight(f)

      def transform_func(x, y, z):
        return mapTo3d.transform(x, y, z + relativeHeight)

      if useZ:
        ogr_geom = ogr.CreateGeometryFromWkb(geometry.asWkb())

        # transform geometry from layer CRS to project CRS
        if ogr_geom.Transform(ogr_transform) != 0:
          logMessage("Failed to transform geometry")
          continue

        # clip geometry
        if ogr_clipGeom and self.geomType == QGis.Line:
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
        if clipGeom and self.geomType in [QGis.Line, QGis.Polygon]:
          geom = geom.intersection(clipGeom)
          if geom is None:
            continue

        # check if geometry is empty
        if geom.isGeosEmpty():
          logMessage("empty geometry skipped")
          continue

        if self.geomType == QGis.Polygon:
          feat.geom = self.geomClass.fromQgsGeometry(geom, z_func, transform_func, self.hasLabel())
          if prop.type_index == 1 and prop.isHeightRelativeToDEM():   # Overlay and relative to DEM
            feat.geom.splitPolygon(self.writer.triangleMesh())

        else:
          feat.geom = self.geomClass.fromQgsGeometry(geom, z_func, transform_func)

      if feat.geom is None:
        continue

      yield feat


def writeVectors(writer, legendInterface=None, progress=None):
  settings = writer.settings
  baseExtent = settings.baseExtent
  progress = progress or dummyProgress
  renderer = QgsMapRenderer()

  layers = []
  if legendInterface is None:
    for parentId in [ObjectTreeItem.ITEM_POINT, ObjectTreeItem.ITEM_LINE, ObjectTreeItem.ITEM_POLYGON]:
      for layerId, properties in settings.get(parentId, {}).iteritems():
        if properties.get("visible", False):
          layers.append([layerId, properties])
  else:
    # use vector layer order in legendInterface
    for layer in legendInterface.layers():
      if layer.type() != QgsMapLayer.VectorLayer:
        continue

      parentId = ObjectTreeItem.parentIdByLayer(layer)
      properties = settings.get(parentId, {}).get(layer.id(), {})
      if properties.get("visible", False):
        layers.append([layer.id(), properties])

  finishedLayers = 0
  for layerId, properties in layers:
    mapLayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
    if mapLayer is None:
      continue

    prop = VectorPropertyReader(writer.objectTypeManager, mapLayer, properties)
    obj_mod = writer.objectTypeManager.module(prop.mod_index)
    if obj_mod is None:
      logMessage("Module not found")
      continue

    # prepare triangle mesh
    geom_type = mapLayer.geometryType()
    if geom_type == QGis.Polygon and prop.type_index == 1 and prop.isHeightRelativeToDEM():   # Overlay
      progress(None, "Initializing triangle mesh for overlay polygons")
      writer.triangleMesh()

    progress(30 + 30 * finishedLayers / len(layers), u"Writing vector layer ({0} of {1}): {2}".format(finishedLayers + 1, len(layers), mapLayer.name()))

    # write layer object
    layer = VectorLayer(writer, mapLayer, prop, obj_mod)
    writer.writeLayer(layer.layerObject(), layer.fieldNames)

    # initialize symbol rendering
    mapLayer.rendererV2().startRender(renderer.rendererContext(), mapLayer.pendingFields() if QGis.QGIS_VERSION_INT >= 20300 else mapLayer)

    # features to export
    request = QgsFeatureRequest()
    clipGeom = None
    if properties.get("radioButton_IntersectingFeatures", False):
      request.setFilterRect(layer.transform.transformBoundingBox(baseExtent.boundingBox(), QgsCoordinateTransform.ReverseTransform))
      if properties.get("checkBox_Clip"):
        extent = baseExtent.clone().scale(0.999999)   # clip with slightly smaller extent than map canvas extent
        clipGeom = extent.geometry()

    for feat in layer.features(request, clipGeom):
      # write geometry
      obj_mod.write(writer, layer, feat)   # writer.writeFeature(layer, feat, obj_mod)

      # stack attributes in writer
      if layer.writeAttrs:
        writer.addAttributes(feat.attributes())

    # write attributes
    if layer.writeAttrs:
      writer.writeAttributes()

    # write materials
    writer.writeMaterials(layer.materialManager)

    mapLayer.rendererV2().stopRender(renderer.rendererContext())
    finishedLayers += 1


def writeSphereTexture(writer):
  # removed (moved to exp_sphere branch)
  pass


def dummyProgress(progress=None, statusMsg=None):
  pass
