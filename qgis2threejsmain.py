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
import os
import codecs
import datetime
import struct

from PyQt4.QtCore import QDir, QSettings
from PyQt4.QtGui import QImage, QPainter
from qgis.core import *

try:
  from osgeo import gdal, ogr, osr
except ImportError:
  import gdal, ogr, osr

from demblock import DEMBlock, DEMBlocks
from rotatedrect import RotatedRect
from geometry import Point, PointGeometry, LineGeometry, PolygonGeometry, TriangleMesh
from datamanager import ImageManager, ModelManager, MaterialManager
from propertyreader import DEMPropertyReader, VectorPropertyReader
from quadtree import DEMQuadTree, DEMQuadList

import gdal2threejs
from gdal2threejs import Raster

import qgis2threejstools as tools
from qgis2threejstools import pyobj2js, logMessage
from settings import debug_mode, def_vals

apiChanged23 = QGis.QGIS_VERSION_INT >= 20300

class ObjectTreeItem:
  ITEM_WORLD = "WORLD"
  ITEM_CONTROLS = "CTRL"
  ITEM_DEM = "DEM"
  ITEM_OPTDEM = "OPTDEM"
  ITEM_POINT = "POINT"
  ITEM_LINE = "LINE"
  ITEM_POLYGON = "POLYGON"
  topItemIds = [ITEM_WORLD, ITEM_CONTROLS, ITEM_DEM, ITEM_OPTDEM, ITEM_POINT, ITEM_LINE, ITEM_POLYGON]
  topItemNames = ["World", "Controls", "DEM", "Additional DEM", "Point", "Line", "Polygon"]
  geomType2id = {QGis.Point: ITEM_POINT, QGis.Line: ITEM_LINE, QGis.Polygon: ITEM_POLYGON}

  @classmethod
  def topItemIndex(cls, id):
    return cls.topItemIds.index(id)

  @classmethod
  def idByGeomType(cls, geomType):
    return cls.geomType2id.get(geomType)

  @classmethod
  def geomTypeById(cls, id):
    for geomType in cls.geomType2id:
      if cls.geomType2id[geomType] == id:
        return geomType
    return None

  @classmethod
  def parentIdByLayer(cls, layer):
    layerType = layer.type()
    if layerType == QgsMapLayer.VectorLayer:
      return cls.idByGeomType(layer.geometryType())

    if layerType == QgsMapLayer.RasterLayer and layer.providerType() == "gdal" and layer.bandCount() == 1:
      return cls.ITEM_OPTDEM

    return None


class MapTo3D:
  def __init__(self, mapCanvas, planeWidth=100, verticalExaggeration=1, verticalShift=0):
    mapSettings = mapCanvas.mapSettings() if apiChanged23 else mapCanvas.mapRenderer()

    # map canvas
    self.rotation = mapSettings.rotation() if QGis.QGIS_VERSION_INT >= 20700 else 0
    self.mapExtent = RotatedRect.fromMapSettings(mapSettings)

    # 3d
    canvas_size = mapSettings.outputSize()
    self.planeWidth = planeWidth
    self.planeHeight = planeWidth * canvas_size.height() / float(canvas_size.width())

    self.verticalExaggeration = verticalExaggeration
    self.verticalShift = verticalShift

    self.multiplier = planeWidth / self.mapExtent.width()
    self.multiplierZ = self.multiplier * verticalExaggeration

  def transform(self, x, y, z=0):
    n = self.mapExtent.normalizePoint(x, y)
    return Point((n.x() - 0.5) * self.planeWidth,
                 (n.y() - 0.5) * self.planeHeight,
                 (z + self.verticalShift) * self.multiplierZ)

  def transformPoint(self, pt):
    return self.transform(pt.x, pt.y, pt.z)

class MemoryWarpRaster(Raster):

  def __init__(self, filename, source_wkt=None, dest_wkt=None):
    Raster.__init__(self, filename)
    self.driver = gdal.GetDriverByName("MEM")
    self.source_wkt = source_wkt
    self.dest_wkt = dest_wkt
    if source_wkt:
      self.ds.SetProjection(str(source_wkt))

  def read(self, width, height, geotransform, dest_wkt=None):
    if dest_wkt is None:
      dest_wkt = self.dest_wkt

    # create a memory dataset
    warped_ds = self.driver.Create("", width, height, 1, gdal.GDT_Float32)
    warped_ds.SetProjection(dest_wkt)
    warped_ds.SetGeoTransform(geotransform)

    # reproject image
    gdal.ReprojectImage(self.ds, warped_ds, None, None, gdal.GRA_Bilinear)

    # load values into an array
    values = []
    fs = "f" * width
    band = warped_ds.GetRasterBand(1)
    for py in range(height):
      values += struct.unpack(fs, band.ReadRaster(0, py, width, 1, width, 1, gdal.GDT_Float32))
    return values

  def readValue(self, x, y, dest_wkt=None):
    """get value at the position using 1px * 1px memory raster"""
    res = 0.1
    geotransform = [x - res / 2, res, 0, y + res / 2, 0, -res]
    return self.read(1, 1, geotransform, dest_wkt)[0]

class FlatRaster:

  def __init__(self, value=0):
    self.value = value

  def name(self):
    return "Flat Plane"

  def read(self, width, height, geotransform, wkt=None):
    return [self.value] * width * height

  def readValue(self, x, y, wkt=None):
    return self.value


class ExportSettings:

  # export mode
  PLAIN_SIMPLE = 0
  PLAIN_MULTI_RES = 1
  SPHERE = 2

  def __init__(self, settings, canvas, pluginManager, localBrowsingMode=True):
    self.data = settings
    self.timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

    # output html file path
    htmlfilename = settings.get("OutputFilename")
    if not htmlfilename:
      htmlfilename = tools.temporaryOutputDir() + "/%s.html" % self.timestamp
    self.htmlfilename = htmlfilename
    self.path_root = os.path.splitext(htmlfilename)[0]
    self.htmlfiletitle = os.path.basename(self.path_root)
    self.title = self.htmlfiletitle

    # load configuration of the template
    self.templateName = settings.get("Template", "")
    templatePath = os.path.join(tools.templateDir(), self.templateName)
    self.templateConfig = tools.getTemplateConfig(templatePath)

    # MapTo3D object
    world = settings.get(ObjectTreeItem.ITEM_WORLD, {})
    baseSize = world.get("lineEdit_BaseSize", def_vals.baseSize)
    verticalExaggeration = world.get("lineEdit_zFactor", def_vals.zExaggeration)
    verticalShift = world.get("lineEdit_zShift", def_vals.zShift)
    self.mapTo3d = MapTo3D(canvas, float(baseSize), float(verticalExaggeration), float(verticalShift))

    self.coordsInWGS84 = world.get("radioButton_WGS84", False)

    self.canvas = canvas
    self.mapSettings = canvas.mapSettings() if apiChanged23 else canvas.mapRenderer()
    self.baseExtent = RotatedRect.fromMapSettings(self.mapSettings)

    self.pluginManager = pluginManager
    self.localBrowsingMode = localBrowsingMode

    self.crs = self.mapSettings.destinationCrs()

    wgs84 = QgsCoordinateReferenceSystem(4326)
    transform = QgsCoordinateTransform(self.crs, wgs84)
    self.wgs84Center = transform.transform(self.baseExtent.center())

    controls = settings.get(ObjectTreeItem.ITEM_CONTROLS, {})
    self.controls = controls.get("comboBox_Controls")
    if not self.controls:
      self.controls = QSettings().value("/Qgis2threejs/lastControls", "OrbitControls.js", type=unicode)

    self.demProvider = None
    self.quadtree = None

    if self.templateConfig.get("type") == "sphere":
      self.exportMode = ExportSettings.SPHERE
      return

    demProperties = settings.get(ObjectTreeItem.ITEM_DEM, {})
    self.demProvider = self.demProviderByLayerId(demProperties["comboBox_DEMLayer"])

    if demProperties.get("radioButton_Simple", False):
      self.exportMode = ExportSettings.PLAIN_SIMPLE
    else:
      self.exportMode = ExportSettings.PLAIN_MULTI_RES
      self.quadtree = createQuadTree(self.baseExtent, demProperties)

  def get(self, key, default=None):
    return self.data.get(key, default)

  def checkValidity(self):
    """return valid as bool, err_msg as str"""
    # check validity of settings
    if self.exportMode == ExportSettings.PLAIN_MULTI_RES and self.quadtree is None:
      return False, u"Focus point/area is not selected."
    return True, ""

  def demProviderByLayerId(self, id):
    if not id:
      return FlatRaster()

    if id.startswith("plugin:"):
      provider = self.pluginManager.findDEMProvider(id[7:])
      if provider:
        return provider(str(self.crs.toWkt()))

      logMessage('Plugin "{0}" not found'.format(id))
      return FlatRaster()

    else:
      layer = QgsMapLayerRegistry.instance().mapLayer(id)
      return MemoryWarpRaster(layer.source(), str(layer.crs().toWkt()), str(self.crs.toWkt()))

    #TODO: rename *Raster to DEMProvider
    #TODO: rename MemoryWarpRaster to GDALDEMProvider

class JSWriter:

  def __init__(self, path_root, multiple_files=False):
    self.path_root = path_root
    self.multiple_files = multiple_files
    self.jsfile = None
    self.jsindex = 0
    self.jsfile_count = 0

  def __del__(self):
    self.closeFile()

  def openFile(self):
    if self.multiple_files:
      jsfilename = self.path_root + "_%d.js" % self.jsindex
    else:
      jsfilename = self.path_root + ".js"
    self.jsfile = codecs.open(jsfilename, "w", "UTF-8")
    self.jsfile_count += 1

  def closeFile(self):
    if self.jsfile:
      self.jsfile.close()
      self.jsfile = None

  def nextFile(self, open_file=False):
    if not self.multiple_files:
      return
    self.closeFile()
    self.jsindex += 1
    if open_file:
      self.openFile()

  def write(self, data):
    if self.jsfile is None:
      self.openFile()
    self.jsfile.write(data)


class ThreejsJSWriter(JSWriter):

  def __init__(self, settings, objectTypeManager, pluginManager, multiple_files=False):
    JSWriter.__init__(self, settings.path_root, multiple_files)

    self.settings = settings
    self.warp_dem = settings.demProvider
    self.objectTypeManager = objectTypeManager
    self.pluginManager = pluginManager

    self.layerCount = 0
    self.currentLayerIndex = 0
    self.currentFeatureIndex = -1
    self.attrs = []
    self.imageManager = ImageManager(settings)
    self.modelManager = ModelManager()
    self.triMesh = {}

  def writeProject(self):
    # write project information
    self.write(u"// Qgis2threejs Project\n")
    settings = self.settings
    extent = self.settings.baseExtent
    rect = extent.unrotatedRect()
    mapTo3d = self.settings.mapTo3d
    wgs84Center = self.settings.wgs84Center

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
    config = self.settings.templateConfig

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
    if self.multiple_files:
      files += map(lambda x: "%s_%s.js" % (filetitle, x), range(self.jsfile_count))
    else:
      files.append("%s.js" % filetitle)

    return map(lambda fn: '<script src="./%s"></script>' % fn, files)

  def triangleMesh(self, dem_width=0, dem_height=0):
    if dem_width == 0 and dem_height == 0:
      prop = DEMPropertyReader(self.settings.get(ObjectTreeItem.ITEM_DEM))
      dem_width = prop.width()
      dem_height = prop.height()

    key = "{0}x{1}".format(dem_width, dem_height)
    if key not in self.triMesh:
      mapTo3d = self.settings.mapTo3d
      hw = 0.5 * mapTo3d.planeWidth
      hh = 0.5 * mapTo3d.planeHeight
      self.triMesh[key] = TriangleMesh(-hw, -hh, hw, hh, dem_width - 1, dem_height - 1)
    return self.triMesh[key]

  def log(self, message):
    logMessage(message)


def exportToThreeJS(settings, legendInterface, objectTypeManager, progress=None):
  progress = progress or dummyProgress

  out_dir = os.path.split(settings.htmlfilename)[0]
  if not QDir(out_dir).exists():
    QDir().mkpath(out_dir)

  # ThreejsJSWriter object
  writer = ThreejsJSWriter(settings, objectTypeManager, bool(settings.exportMode == ExportSettings.PLAIN_MULTI_RES))
  writer.openFile()

  # read configuration of the template
  templateConfig = settings.templateConfig
  templatePath = templateConfig["path"]

  if settings.exportMode == ExportSettings.SPHERE:
    # render texture for sphere and write it
    progress(5, "Rendering texture")
    writeSphereTexture(writer)
  else:
    # plain type
    writer.writeProject()
    progress(5, "Writing DEM")

    # write primary DEM
    demProperties = settings.get(ObjectTreeItem.ITEM_DEM)
    if settings.exportMode == ExportSettings.PLAIN_SIMPLE:
      writeSimpleDEM(writer, demProperties, progress)
    else:
      writeMultiResDEM(writer, demProperties, progress)
      writer.nextFile()

    # write additional DEM(s)
    primaryDEMLayerId = demProperties["comboBox_DEMLayer"]
    for layerId, properties in settings.get(ObjectTreeItem.ITEM_OPTDEM, {}).iteritems():
      if properties.get("visible", False) and layerId != primaryDEMLayerId and QgsMapLayerRegistry.instance().mapLayer(layerId):
        writeSimpleDEM(writer, properties)

    progress(30, "Writing vector data")

    # write vector data
    writeVectors(writer, legendInterface, progress)

  # write images and model data
  progress(60, "Writing texture images")
  writer.writeImages()
  writer.writeModelData()
  writer.closeFile()

  progress(90, "Copying library files")

  # copy files
  tools.copyFiles(writer.filesToCopy(), out_dir)

  # generate html file
  options = []
  world = settings.get(ObjectTreeItem.ITEM_WORLD, {})
  if world.get("radioButton_Color", False):
    options.append("option.bgcolor = {0};".format(world.get("lineEdit_Color", 0)))

  # read html template
  with codecs.open(templatePath, "r", "UTF-8") as f:
    html = f.read()

  html = html.replace("${title}", settings.title)
  html = html.replace("${controls}", '<script src="./threejs/%s"></script>' % settings.controls)    #TODO: move to writer.scripts()
  html = html.replace("${options}", "\n".join(options))
  html = html.replace("${scripts}", "\n".join(writer.scripts()))

  # write html
  with codecs.open(settings.htmlfilename, "w", "UTF-8") as f:
    f.write(html)

  return True

def writeSimpleDEM(writer, properties, progress=None):
  settings = writer.settings
  mapTo3d = settings.mapTo3d
  progress = progress or dummyProgress

  prop = DEMPropertyReader(properties)    #TODO: prop_reader

  # warp dem    #TODO: rename to provider
  warp_dem = settings.demProviderByLayerId(prop.layerId)
  if isinstance(warp_dem, MemoryWarpRaster):
    demLayer = QgsMapLayerRegistry.instance().mapLayer(prop.layerId)
    layerName = demLayer.name()
  else:
    demLayer = None
    layerName = warp_dem.name()

  # layer
  layer = DEMLayer(writer, demLayer, prop)
  lyr = layer.layerObject()
  lyr.update({"name": layerName})
  lyrIdx = writer.writeLayer(lyr)

  # material option
  texture_scale = properties["comboBox_TextureSize"] / 100
  transparency = properties["spinBox_demtransp"]
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
    mat = layer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], transparency, True)

  #elif properties.get("radioButton_Wireframe", False):
  #  block["m"] = layer.materialManager.getWireframeIndex(properties["lineEdit_Color"], transparency)

  # get DEM values
  dem_width, dem_height = prop.width(), prop.height()
  dem_values = warp_dem.read(dem_width, dem_height, settings.baseExtent.geotransform(dem_width, dem_height))

  # DEM block
  block = DEMBlock(dem_width, dem_height, dem_values, mapTo3d.planeWidth, mapTo3d.planeHeight, 0, 0)
  block.zShift(mapTo3d.verticalShift)
  block.zScale(mapTo3d.multiplierZ)
  block.set("m", mat)

  surroundings = properties.get("checkBox_Surroundings", False) if demLayer else False    #TODO: prop.layerId
  if surroundings:
    blocks = DEMBlocks()
    blocks.appendBlock(block)
    blocks.appendBlocks(surroundingDEMBlocks(writer, layer, warp_dem, properties, progress))
    blocks.processEdges()
    blocks.write(writer)

    writer.write("lyr.stats = {0};\n".format(pyobj2js(blocks.stats())))

  else:
    # clipping
    if properties.get("checkBox_Clip", False):
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


def dissolvePolygonsOnCanvas(writer, layer):
  """dissolve polygons of the layer and clip the dissolution with base extent"""
  settings = writer.settings
  baseExtent = settings.baseExtent
  baseExtentGeom = baseExtent.geometry()
  rotation = baseExtent.rotation()
  transform = QgsCoordinateTransform(layer.crs(), settings.crs)

  combi = None
  request = QgsFeatureRequest()
  request.setFilterRect(transform.transformBoundingBox(baseExtent.boundingBox(), QgsCoordinateTransform.ReverseTransform))
  for f in layer.getFeatures(request):
    geometry = f.geometry()
    if geometry is None:
      logMessage("null geometry skipped")
      continue

    # coordinate transformation - layer crs to project crs
    geom = QgsGeometry(geometry)
    if geom.transform(transform) != 0:
      logMessage("Failed to transform geometry")
      continue

    # check if geometry intersects with the base extent (rotated rect)
    if rotation and not baseExtentGeom.intersects(geom):
      continue

    if combi:
      combi = combi.combine(geom)
    else:
      combi = geom

  # clip geom with slightly smaller extent than base extent
  # to make sure that the clipped polygon stays within the base extent
  geom = combi.intersection(baseExtent.clone().scale(0.999999).geometry())
  if geom is None:
    return None

  # check if geometry is empty
  if geom.isGeosEmpty():
    logMessage("empty geometry")
    return None

  return geom


#TODO: remove
def roughenEdges(width, height, values, interval):
  if interval == 1:
    return

  for y in [0, height - 1]:
    for x1 in range(interval, width, interval):
      x0 = x1 - interval
      z0 = values[x0 + width * y]
      z1 = values[x1 + width * y]
      for xx in range(1, interval):
        z = (z0 * (interval - xx) + z1 * xx) / interval
        values[x0 + xx + width * y] = z

  for x in [0, width - 1]:
    for y1 in range(interval, height, interval):
      y0 = y1 - interval
      z0 = values[x + width * y0]
      z1 = values[x + width * y1]
      for yy in range(1, interval):
        z = (z0 * (interval - yy) + z1 * yy) / interval
        values[x + width * (y0 + yy)] = z


def surroundingDEMBlocks(writer, layer, warp_dem, properties, progress=None):
  settings = writer.settings
  mapSettings = settings.mapSettings
  mapTo3d = settings.mapTo3d
  baseExtent = settings.baseExtent
  progress = progress or dummyProgress

  # options
  size = properties["spinBox_Size"]
  roughening = properties["spinBox_Roughening"]
  texture_scale = properties["comboBox_TextureSize"] / 100
  transparency = properties["spinBox_demtransp"]
  transp_background = properties.get("checkBox_TransparentBackground", False)

  prop = DEMPropertyReader(properties)
  dem_width = (prop.width() - 1) / roughening + 1
  dem_height = (prop.height() - 1) / roughening + 1

  # texture size
  canvas_size = mapSettings.outputSize()
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
      mat = layer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], transparency, True)

    # DEM block
    dem_values = warp_dem.read(dem_width, dem_height, extent.geotransform(dem_width, dem_height))
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
  mapTo3d = settings.mapTo3d
  baseExtent = settings.baseExtent
  progress = progress or dummyProgress

  prop = DEMPropertyReader(properties)

  # provider    #TODO: rename to provider
  warp_dem = settings.demProviderByLayerId(prop.layerId)
  if isinstance(warp_dem, MemoryWarpRaster):
    demLayer = QgsMapLayerRegistry.instance().mapLayer(prop.layerId)
    layerName = demLayer.name()
  else:
    demLayer = None
    layerName = warp_dem.name()

  # layer
  layer = DEMLayer(writer, demLayer, prop)
  lyr = layer.layerObject()
  lyr.update({"name": layerName})
  lyrIdx = writer.writeLayer(lyr)

  # quad tree
  quadtree = settings.quadtree
  if quadtree is None:
    return

  # (currently) dem size is 2 ^ quadtree.height * a + 1, where a is larger integer than 0
  # with smooth resolution change, this is not necessary
  dem_width = dem_height = max(64, 2 ** quadtree.height) + 1

  # material options
  texture_scale = properties["comboBox_TextureSize"] / 100
  transparency = properties["spinBox_demtransp"]
  transp_background = properties.get("checkBox_TransparentBackground", False)
  layerImageIds = properties.get("layerImageIds", [])

  def materialIndex(extent, image_width, image_height):
    # display type
    if properties.get("radioButton_MapCanvas", False):
      return layer.materialManager.getMapImageIndex(image_width, image_height, extent, transparency, transp_background)

    elif properties.get("radioButton_LayerImage", False):
      return layer.materialManager.getLayerImageIndex(layerImageIds, image_width, image_height, extent, transparency, transp_background)

    else:   #.get("radioButton_SolidColor", False)
      return layer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], transparency, True)

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
    dem_values = warp_dem.read(dem_width, dem_height, extent.geotransform(dem_width, dem_height))

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
      centerQuads.addQuad(quad, quad.dem_values)    #TODO: DEMQuadNode
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
    mapTo3d = self.writer.settings.mapTo3d
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
    mapTo3d = settings.mapTo3d
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
          z_func = lambda x, y: self.writer.warp_dem.readValue(x, y)
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


def writeVectors(writer, legendInterface, progress=None):
  settings = writer.settings
  baseExtent = settings.baseExtent
  progress = progress or dummyProgress
  renderer = QgsMapRenderer()

  layers = []
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
    mapLayer.rendererV2().startRender(renderer.rendererContext(), mapLayer.pendingFields() if apiChanged23 else mapLayer)

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

def createQuadTree(extent, p):
  """
  args:
    p -- demProperties
  """
  try:
    cx, cy, w, h = map(float, [p["lineEdit_centerX"], p["lineEdit_centerY"], p["lineEdit_rectWidth"], p["lineEdit_rectHeight"]])
  except ValueError:
    return None

  # normalize
  c = extent.normalizePoint(cx, cy)
  hw = 0.5 * w / extent.width()
  hh = 0.5 * h / extent.height()

  quadtree = DEMQuadTree()
  if not quadtree.buildTreeByRect(QgsRectangle(c.x() - hw, c.y() - hh, c.x() + hw, c.y() + hh), p["spinBox_Height"]):
    return None

  return quadtree

def dummyProgress(progress=None, statusMsg=None):
  pass
