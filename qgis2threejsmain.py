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

from PyQt4.QtCore import QDir, QSettings, qDebug
from PyQt4.QtGui import QImage, QPainter
from qgis.core import *

try:
  from osgeo import gdal
except ImportError:
  import gdal

from rotatedrect import RotatedRect
from geometry import Point, PointGeometry, LineGeometry, PolygonGeometry
from datamanager import ImageManager, ModelManager, MaterialManager
from propertyreader import DEMPropertyReader, VectorPropertyReader
from quadtree import QuadTree, DEMQuadList

import gdal2threejs
from gdal2threejs import Raster

import qgis2threejstools as tools
from qgis2threejstools import pyobj2js
from settings import debug_mode, def_vals

apiChanged23 = QGis.QGIS_VERSION_INT >= 20300

# used for tree widget and properties
class ObjectTreeItem:
  topItemNames = ["World", "Controls", "DEM", "Additional DEM", "Point", "Line", "Polygon"]
  ITEM_WORLD = 0
  ITEM_CONTROLS = 1
  ITEM_DEM = 2
  ITEM_OPTDEM = 3
  ITEM_POINT = 4
  ITEM_LINE = 5
  ITEM_POLYGON = 6


class MapTo3D:
  def __init__(self, mapCanvas, planeWidth=100, verticalExaggeration=1, verticalShift=0):   #TODO: mapSettings
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
  def __init__(self, filename, wkt=None):   #TODO: source_wkt and dest_wkt
    Raster.__init__(self, filename)
    self.driver = gdal.GetDriverByName("MEM")
    if wkt:
      self.ds.SetProjection(str(wkt))

  def read(self, width, height, wkt, geotransform):
    # create a memory dataset
    warped_ds = self.driver.Create("", width, height, 1, gdal.GDT_Float32)
    warped_ds.SetProjection(wkt)
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

  def readValue(self, wkt, x, y):
    # get value at the position using 1px * 1px memory raster
    res = 0.1
    geotransform = [x - res / 2, res, 0, y + res / 2, 0, -res]
    return self.read(1, 1, wkt, geotransform)[0]

class FlatRaster:
  def __init__(self, value=0):
    self.value = value

  def read(self, width, height, wkt, geotransform):
    return [self.value] * width * height

  def readValue(self, wkt, x, y):
    return self.value


class ExportSettings:

  # export mode
  PLAIN_SIMPLE = 0
  PLAIN_MULTI_RES = 1
  SPHERE = 2

  def __init__(self, htmlfilename, templateConfig, canvas, properties, localBrowsingMode=True):

    self.timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

    if not htmlfilename:
      htmlfilename = tools.temporaryOutputDir() + "/%s.html" % self.timestamp
    self.htmlfilename = htmlfilename
    self.path_root = os.path.splitext(htmlfilename)[0]
    self.htmlfiletitle = os.path.basename(self.path_root)
    self.title = self.htmlfiletitle

    self.templateConfig = templateConfig

    # MapTo3D object
    world = properties[ObjectTreeItem.ITEM_WORLD] or {}
    baseSize = world.get("lineEdit_BaseSize", def_vals.baseSize)
    verticalExaggeration = world.get("lineEdit_zFactor", def_vals.zExaggeration)
    verticalShift = world.get("lineEdit_zShift", def_vals.zShift)
    self.mapTo3d = MapTo3D(canvas, float(baseSize), float(verticalExaggeration), float(verticalShift))

    self.coordsInWGS84 = world.get("radioButton_WGS84", False)

    self.canvas = canvas
    self.mapSettings = canvas.mapSettings() if apiChanged23 else canvas.mapRenderer()
    self.baseExtent = RotatedRect.fromMapSettings(self.mapSettings)

    self.properties = properties

    self.localBrowsingMode = localBrowsingMode

    self.crs = self.mapSettings.destinationCrs()

    wgs84 = QgsCoordinateReferenceSystem(4326)
    transform = QgsCoordinateTransform(self.crs, wgs84)
    self.wgs84Center = transform.transform(self.baseExtent.center())

    self.image_basesize = 256

    controls = properties[ObjectTreeItem.ITEM_CONTROLS] or {}
    self.controls = controls.get("comboBox_Controls")
    if not self.controls:
      self.controls = QSettings().value("/Qgis2threejs/lastControls", "OrbitControls.js", type=unicode)

    self.demLayer = None
    self.quadtree = None
    if templateConfig.get("type") == "sphere":
      self.exportMode = ExportSettings.SPHERE
      return

    demProperties = properties[ObjectTreeItem.ITEM_DEM]
    demLayerId = demProperties["comboBox_DEMLayer"]
    if demLayerId:
      self.demLayer = QgsMapLayerRegistry.instance().mapLayer(demLayerId)

    if demProperties.get("radioButton_Simple", False):
      self.exportMode = ExportSettings.PLAIN_SIMPLE
    else:
      self.exportMode = ExportSettings.PLAIN_MULTI_RES
      self.quadtree = createQuadTree(self.baseExtent, demProperties)


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

  def __init__(self, settings, objectTypeManager, multiple_files=False):
    JSWriter.__init__(self, settings.path_root, multiple_files)

    self.settings = settings
    self.objectTypeManager = objectTypeManager

    self.layerCount = 0
    self.currentLayerIndex = 0
    self.currentFeatureIndex = -1
    self.attrs = []

    if settings.demLayer:
      self.warp_dem = MemoryWarpRaster(settings.demLayer.source(), str(settings.demLayer.crs().toWkt()))
    else:
      self.warp_dem = FlatRaster()

    self.imageManager = ImageManager(settings)
    self.modelManager = ModelManager()
    self.triMesh = None

  def writeProject(self):
    # write project information
    self.write(u"// Qgis2threejs Project\n")
    settings = self.settings
    extent = self.settings.baseExtent
    mapTo3d = self.settings.mapTo3d
    wgs84Center = self.settings.wgs84Center

    args = {"title": settings.title,
            "crs": unicode(settings.crs.authid()),
            "proj": settings.crs.toProj4(),
            "baseExtent": [extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()],
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

  def triangleMesh(self):
    if self.triMesh is None:
      self.triMesh = TriangleMesh.createFromExportSettings(self.settings)
    return self.triMesh

  def log(self, message):
    QgsMessageLog.logMessage(message, "Qgis2threejs")


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
    demProperties = settings.properties[ObjectTreeItem.ITEM_DEM]
    if settings.exportMode == ExportSettings.PLAIN_SIMPLE:
      writeSimpleDEM(writer, demProperties, progress)
    else:
      writeMultiResDEM(writer, demProperties, progress)
      writer.nextFile()

    # write additional DEM(s)
    primaryDEMLayerId = demProperties["comboBox_DEMLayer"]
    for layerId, properties in settings.properties[ObjectTreeItem.ITEM_OPTDEM].iteritems():
      if layerId != primaryDEMLayerId and properties.get("visible", False):
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
  world = settings.properties[ObjectTreeItem.ITEM_WORLD] or {}
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

  prop = DEMPropertyReader(properties)
  dem_width = prop.width()
  dem_height = prop.height()

  # warp dem
  wkt = str(settings.crs.toWkt())

  demLayer = QgsMapLayerRegistry.instance().mapLayer(prop.layerId) if prop.layerId else None
  if demLayer:
    layerName = demLayer.name()
    warp_dem = MemoryWarpRaster(demLayer.source(), str(demLayer.crs().toWkt()))
  else:
    layerName = "Flat plane"
    warp_dem = FlatRaster()

  dem_values = warp_dem.read(dem_width, dem_height, wkt, settings.baseExtent.geotransform(dem_width, dem_height))

  # calculate statistics
  stats = {"max": max(dem_values), "min": min(dem_values)}

  # shift and scale
  if mapTo3d.verticalShift != 0:
    dem_values = map(lambda x: x + mapTo3d.verticalShift, dem_values)
  if mapTo3d.multiplierZ != 1:
    dem_values = map(lambda x: x * mapTo3d.multiplierZ, dem_values)

  surroundings = properties.get("checkBox_Surroundings", False)
  if surroundings:
    roughenEdges(dem_width, dem_height, dem_values, properties["spinBox_Roughening"])

  # layer
  layer = DEMLayer(writer, demLayer, prop)
  lyr = {"type": "dem", "name": layerName, "stats": stats}
  lyr["q"] = 1    #queryable
  lyrIdx = writer.writeLayer(lyr)

  # dem block
  block = {"width": dem_width, "height": dem_height}
  block["plane"] = {"width": mapTo3d.planeWidth, "height": mapTo3d.planeHeight, "offsetX": 0, "offsetY": 0}

  # material option
  transparency = properties["spinBox_demtransp"]
  transp_background = properties.get("checkBox_TransparentBackground", False)

  # display type
  if properties.get("radioButton_MapCanvas", False):
    block["m"] = layer.materialManager.getCanvasImageIndex(transparency, transp_background)

  elif properties.get("radioButton_LayerImage", False):
    layerid = properties.get("comboBox_ImageLayer")
    size = settings.mapSettings.outputSize()
    block["m"] = layer.materialManager.getLayerImageIndex(layerid, size.width(), size.height(), settings.baseExtent, transparency, transp_background)

  elif properties.get("radioButton_ImageFile", False):
    filepath = properties.get("lineEdit_ImageFile", "")
    block["m"] = layer.materialManager.getImageFileIndex(filepath, transparency, transp_background, True)

  elif properties.get("radioButton_SolidColor", False):
    block["m"] = layer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], transparency, True)

  #elif properties.get("radioButton_Wireframe", False):
  #  block["m"] = layer.materialManager.getWireframeIndex(properties["lineEdit_Color"], transparency)

  # shading (whether compute normals)
  if properties.get("checkBox_Shading", True):
    block["shading"] = True

  if not surroundings and properties.get("checkBox_Sides", False):
    block["s"] = True

  if not surroundings and properties.get("checkBox_Frame", False):
    block["frame"] = True

  # write central block
  writer.write("bl = lyr.addBlock({0});\n".format(pyobj2js(block)))
  writer.write("bl.data = [{0}];\n".format(",".join(map(gdal2threejs.formatValue, dem_values))))

  # write surrounding dems
  if surroundings:
    writeSurroundingDEM(writer, layer, warp_dem, stats, properties, progress)
    # overwrite stats
    writer.write("lyr.stats = {0};\n".format(pyobj2js(stats)))

  writer.writeMaterials(layer.materialManager)

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


def writeSurroundingDEM(writer, layer, warp_dem, stats, properties, progress=None):
  settings = writer.settings
  mapSettings = settings.mapSettings
  mapTo3d = settings.mapTo3d
  baseExtent = settings.baseExtent
  progress = progress or dummyProgress

  # options
  size = properties["spinBox_Size"]
  roughening = properties["spinBox_Roughening"]
  transparency = properties["spinBox_demtransp"]
  transp_background = properties.get("checkBox_TransparentBackground", False)

  prop = DEMPropertyReader(properties)
  dem_width = (prop.width() - 1) / roughening + 1
  dem_height = (prop.height() - 1) / roughening + 1

  wkt = str(settings.crs.toWkt())

  # texture image size
  canvas_size = mapSettings.outputSize()
  hpw = float(canvas_size.height()) / canvas_size.width()
  if hpw < 1:
    image_width = settings.image_basesize
    image_height = round(image_width * hpw)
    #image_height = settings.image_basesize * max(1, int(round(1 / hpw)))    # not rendered expectedly
  else:
    image_height = settings.image_basesize
    image_width = round(image_height / hpw)

  center = baseExtent.center()
  rotation = baseExtent.rotation()

  plane_index = 1
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

    # warp dem
    dem_values = warp_dem.read(dem_width, dem_height, wkt, extent.geotransform(dem_width, dem_height))

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

    # generate javascript data file
    # dem block
    block = {"width": dem_width, "height": dem_height}
    block["plane"] = {"width": mapTo3d.planeWidth, "height": mapTo3d.planeHeight,
                      "offsetX": mapTo3d.planeWidth * sx, "offsetY": mapTo3d.planeHeight * sy}

    # display type
    if properties.get("radioButton_MapCanvas", False):
      block["m"] = layer.materialManager.getMapImageIndex(image_width, image_height, extent, transparency, transp_background)

    elif properties.get("radioButton_LayerImage", False):
      layerid = properties.get("comboBox_ImageLayer")
      block["m"] = layer.materialManager.getLayerImageIndex(layerid, image_width, image_height, extent, transparency, transp_background)

    elif properties.get("radioButton_SolidColor", False):
      block["m"] = layer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], transparency, True)

    # shading (whether compute normals)
    if properties.get("checkBox_Shading", True):
      block["shading"] = True

    # write block
    writer.write("bl = lyr.addBlock({0});\n".format(pyobj2js(block)))
    writer.write("bl.data = [{0}];\n".format(",".join(map(gdal2threejs.formatValue, dem_values))))
    plane_index += 1

def writeMultiResDEM(writer, properties, progress=None):
  settings = writer.settings
  mapSettings = settings.mapSettings
  mapTo3d = settings.mapTo3d
  baseExtent = settings.baseExtent
  progress = progress or dummyProgress

  prop = DEMPropertyReader(properties)
  demLayer = QgsMapLayerRegistry.instance().mapLayer(prop.layerId)
  if demLayer is None:
    return

  warp_dem = MemoryWarpRaster(demLayer.source(), str(demLayer.crs().toWkt()))

  # material options
  transparency = properties["spinBox_demtransp"]
  transp_background = properties.get("checkBox_TransparentBackground", False)
  imageLayerId = properties.get("comboBox_ImageLayer")

  # TODO:
  def writeBlock(quad_rect, image_width, image_height):
    pass

  # layer
  layer = DEMLayer(writer, demLayer, prop)
  lyr = {"type": "dem", "name": demLayer.name()}
  lyr["q"] = 1    #queryable
  lyrIdx = writer.writeLayer(lyr)

  # image size
  canvas_size = mapSettings.outputSize()
  hpw = float(canvas_size.height()) / canvas_size.width()
  if hpw < 1:
    image_width = settings.image_basesize
    image_height = round(image_width * hpw)
  else:
    image_height = settings.image_basesize
    image_width = round(image_height / hpw)

  # quad tree
  quadtree = settings.quadtree
  quads = quadtree.quads()

  # (currently) dem size should be 2 ^ quadtree.height * a + 1, where a is larger integer than 0
  # with smooth resolution change, this is not necessary
  dem_width = dem_height = max(64, 2 ** quadtree.height) + 1

  wkt = str(settings.crs.toWkt())

  unites_center = True
  centerQuads = DEMQuadList(dem_width, dem_height)
  stats = None
  plane_index = 0
  for i, quad in enumerate(quads):
    progress(30 * i / len(quads) + 5)

    # block extent
    rect = quad.rect
    extent = baseExtent.subdivide(rect)

    # warp dem
    dem_values = warp_dem.read(dem_width, dem_height, wkt, extent.geotransform(dem_width, dem_height))
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

    # calculate DEM values on edges to combine with next DEM block with different resolution
    neighbors = quadtree.neighbors(quad)
    for direction, neighbor in enumerate(neighbors):
      if neighbor is None:
        continue
      interval = 2 ** (quad.height - neighbor.height)
      if interval > 1:
        if direction == QuadTree.UP or direction == QuadTree.DOWN:
          y = 0 if direction == QuadTree.UP else dem_height - 1
          for x1 in range(interval, dem_width, interval):
            x0 = x1 - interval
            z0 = dem_values[x0 + dem_width * y]
            z1 = dem_values[x1 + dem_width * y]
            for xx in range(1, interval):
              z = (z0 * (interval - xx) + z1 * xx) / interval
              dem_values[x0 + xx + dem_width * y] = z
        else:   # LEFT or RIGHT
          x = 0 if direction == QuadTree.LEFT else dem_width - 1
          for y1 in range(interval, dem_height, interval):
            y0 = y1 - interval
            z0 = dem_values[x + dem_width * y0]
            z1 = dem_values[x + dem_width * y1]
            for yy in range(1, interval):
              z = (z0 * (interval - yy) + z1 * yy) / interval
              dem_values[x + dem_width * (y0 + yy)] = z

    if unites_center and quad.height == quadtree.height:
      centerQuads.addQuad(quad, dem_values)
    else:
      npt = baseExtent.normalizePoint(extent.center().x(), extent.center().y())
      block = {"width": dem_width, "height": dem_height}
      block["plane"] = {"width": rect.width() * mapTo3d.planeWidth,
                        "height": rect.height() * mapTo3d.planeHeight,
                        "offsetX": (npt.x() - 0.5) * mapTo3d.planeWidth,
                        "offsetY": (npt.y() - 0.5) * mapTo3d.planeHeight}

      # display type
      if properties.get("radioButton_MapCanvas", False):
        block["m"] = layer.materialManager.getMapImageIndex(image_width, image_height, extent, transparency, transp_background)

      elif properties.get("radioButton_LayerImage", False):
        block["m"] = layer.materialManager.getLayerImageIndex(imageLayerId, image_width, image_height, extent, transparency, transp_background)

      elif properties.get("radioButton_SolidColor", False):
        block["m"] = layer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], transparency, True)

      # shading (whether compute normals)
      if properties.get("checkBox_Shading", True):
        block["shading"] = True

      # write block
      writer.nextFile(True)
      writer.write("bl = lyr.addBlock({0});\n".format(pyobj2js(block)))
      writer.write("bl.data = [{0}];\n".format(",".join(map(gdal2threejs.formatValue, dem_values))))
      plane_index += 1

  if unites_center:
    dem_width = (dem_width - 1) * centerQuads.width() + 1
    dem_height = (dem_height - 1) * centerQuads.height() + 1
    dem_values = centerQuads.unitedDEM()

    # block extent
    rect = centerQuads.rect()
    extent = baseExtent.subdivide(rect)
    npt = baseExtent.normalizePoint(extent.center().x(), extent.center().y())

    block = {"width": dem_width, "height": dem_height}
    block["plane"] = {"width": rect.width() * mapTo3d.planeWidth,
                      "height": rect.height() * mapTo3d.planeHeight,
                      "offsetX": (npt.x() - 0.5) * mapTo3d.planeWidth,
                      "offsetY": (npt.y() - 0.5) * mapTo3d.planeHeight}

    if hpw < 1:
      image_width = settings.image_basesize * centerQuads.width()
      image_height = round(image_width * hpw)
    else:
      image_height = settings.image_basesize * centerQuads.height()
      image_width = round(image_height / hpw)

    # display type
    if properties.get("radioButton_MapCanvas", False):
      block["m"] = layer.materialManager.getMapImageIndex(image_width, image_height, extent, transparency, transp_background)

    elif properties.get("radioButton_LayerImage", False):
      block["m"] = layer.materialManager.getLayerImageIndex(imageLayerId, image_width, image_height, extent, transparency, transp_background)

    elif properties.get("radioButton_SolidColor", False):
      block["m"] = layer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], transparency, True)

    # write block
    writer.nextFile(True)
    writer.write("bl = lyr.addBlock({0});\n".format(pyobj2js(block)))
    writer.write("bl.data = [{0}];\n".format(",".join(map(gdal2threejs.formatValue, dem_values))))
    plane_index += 1

  writer.write("lyr.stats = {0};\n".format(pyobj2js(stats)))
  writer.writeMaterials(layer.materialManager)

class TriangleMesh:

  # 0 - 3
  # | / |
  # 1 - 2

  def __init__(self, xmin, ymin, xmax, ymax, x_segments, y_segments):
    self.flen = 0
    self.quadrangles = []
    self.spatial_index = QgsSpatialIndex()

    xres = (xmax - xmin) / x_segments
    yres = (ymax - ymin) / y_segments
    for y in range(y_segments):
      for x in range(x_segments):
        pt0 = QgsPoint(xmin + x * xres, ymax - y * yres)
        pt1 = QgsPoint(xmin + x * xres, ymax - (y + 1) * yres)
        pt2 = QgsPoint(xmin + (x + 1) * xres, ymax - (y + 1) * yres)
        pt3 = QgsPoint(xmin + (x + 1) * xres, ymax - y * yres)
        self._addQuadrangle(pt0, pt1, pt2, pt3)

  def _addQuadrangle(self, pt0, pt1, pt2, pt3):
    f = QgsFeature(self.flen)
    f.setGeometry(QgsGeometry.fromPolygon([[pt0, pt1, pt2, pt3, pt0]]))
    self.quadrangles.append(f)
    self.spatial_index.insertFeature(f)
    self.flen += 1

  def intersects(self, geom):
    for fid in self.spatial_index.intersects(geom.boundingBox()):
      quad = self.quadrangles[fid].geometry()
      if quad.intersects(geom):
        yield quad

  def splitPolygon(self, geom):
    polygons = []
    for quad in self.intersects(geom):
      pts = quad.asPolygon()[0]
      tris = [[[pts[0], pts[1], pts[3], pts[0]]], [[pts[3], pts[1], pts[2], pts[3]]]]
      if geom.contains(quad):
        polygons += tris
      else:
        for i, tri in enumerate(map(QgsGeometry.fromPolygon, tris)):
          if geom.contains(tri):
            polygons.append(tris[i])
          elif geom.intersects(tri):
            poly = geom.intersection(tri)
            if poly.isMultipart():
              polygons += poly.asMultiPolygon()
            else:
              polygons.append(poly.asPolygon())
    return polygons

  @classmethod
  def createFromExportSettings(cls, settings):
    prop = DEMPropertyReader(settings.properties[ObjectTreeItem.ITEM_DEM])
    dem_width = prop.width()
    dem_height = prop.height()
    extent = settings.baseExtent
    triMesh = TriangleMesh(extent.xMinimum(), extent.yMinimum(),
                           extent.xMaximum(), extent.yMaximum(),
                           dem_width - 1, dem_height - 1)
    return triMesh


class Feature:

  def __init__(self, writer, layer):
    self.writer = writer
    self.layer = layer

    self.prop = layer.prop
    self.wkt = layer.wkt
    self.transform = layer.transform
    self.geomType = layer.geomType
    self.geomClass = layer.geomClass
    self.hasLabel = layer.hasLabel

    self.feat = None
    self.geom = None

  def setQgsFeature(self, feat, clipGeom=None):
    self.feat = feat
    self.geom = None

    geom = feat.geometry()
    if geom is None:
      qDebug("null geometry skipped")
      return

    # coordinate transformation - layer crs to project crs
    geom.transform(self.transform)

    # clip geometry
    if clipGeom and self.geomType in [QGis.Line, QGis.Polygon]:
      geom = geom.intersection(clipGeom)
      if geom is None:
        return

    # check if geometry is empty
    if geom.isGeosEmpty():
      qDebug("empty geometry skipped")
      return

    # z_func: function to get z coordinate at given point (x, y)
    if self.prop.isHeightRelativeToDEM():
      # calculate elevation with dem
      z_func = lambda x, y: self.writer.warp_dem.readValue(self.wkt, x, y)
    else:
      z_func = lambda x, y: 0

    # transform_func: function to transform the map coordinates to 3d coordinates
    mapTo3d = self.writer.settings.mapTo3d
    relativeHeight = self.prop.relativeHeight(feat)
    def transform_func(x, y, z):
      return mapTo3d.transform(x, y, z + relativeHeight)

    if self.geomType == QGis.Polygon:
      triMesh = None
      if self.prop.type_index == 1 and self.prop.isHeightRelativeToDEM():   # Overlay
        z_func = lambda x, y: 0
        triMesh = self.writer.triangleMesh()
      self.geom = self.geomClass.fromQgsGeometry(geom, z_func, transform_func, self.hasLabel, triMesh)
    elif self.prop.useZ():
      self.geom = self.geomClass.fromWkb25D(geom.asWkb(), transform_func)
    else:
      self.geom = self.geomClass.fromQgsGeometry(geom, z_func, transform_func)

  def relativeHeight(self):
    return self.prop.relativeHeight(self.feat)

  def color(self):
    return self.prop.color(self.feat)

  def transparency(self):
    return self.prop.transparency(self.feat)

  def propValues(self):
    return self.prop.values(self.feat)


class Layer:

  def __init__(self, writer, layer, prop):
    self.writer = writer
    self.layer = layer
    self.prop = prop

    self.materialManager = MaterialManager()


class DEMLayer(Layer):
  pass


class VectorLayer(Layer):

  geomType2Class = {QGis.Point: PointGeometry, QGis.Line: LineGeometry, QGis.Polygon: PolygonGeometry}

  def __init__(self, writer, layer, prop):
    Layer.__init__(self, writer, layer, prop)

    crs = writer.settings.crs
    self.wkt = str(crs.toWkt())
    self.transform = QgsCoordinateTransform(layer.crs(), crs)
    self.geomType = layer.geometryType()
    self.geomClass = self.geomType2Class.get(self.geomType)
    self.hasLabel = prop.properties.get("checkBox_ExportAttrs", False) and prop.properties.get("comboBox_Label") is not None


def writeVectors(writer, legendInterface, progress=None):
  settings = writer.settings
  baseExtent = settings.baseExtent
  mapTo3d = settings.mapTo3d
  progress = progress or dummyProgress
  renderer = QgsMapRenderer()

  layers = []
  for layer in legendInterface.layers():
    if layer.type() != QgsMapLayer.VectorLayer or layer.geometryType() not in [QGis.Point, QGis.Line, QGis.Polygon]:
      continue

    parentId = ObjectTreeItem.ITEM_POINT + layer.geometryType()
    properties = settings.properties[parentId].get(layer.id(), {})
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
      qDebug("Module not found")
      continue

    # prepare triangle mesh
    geom_type = mapLayer.geometryType()
    if geom_type == QGis.Polygon and prop.type_index == 1 and prop.isHeightRelativeToDEM():   # Overlay
      progress(None, "Initializing triangle mesh for overlay polygons")
      writer.triangleMesh()

    progress(30 + 30 * finishedLayers / len(layers), u"Writing vector layer ({0} of {1}): {2}".format(finishedLayers + 1, len(layers), mapLayer.name()))

    # layer object
    layer = VectorLayer(writer, mapLayer, prop)
    lyr = {"name": mapLayer.name()}
    lyr["type"] = {QGis.Point: "point", QGis.Line: "line", QGis.Polygon: "polygon"}.get(geom_type, "")
    lyr["q"] = 1    #queryable
    lyr["objType"] = prop.type_name

    if geom_type == QGis.Polygon and prop.type_index == 1:   # Overlay
      lyr["am"] = "relative" if prop.isHeightRelativeToDEM() else "absolute"    # altitude mode

    # make list of field names
    writeAttrs = properties.get("checkBox_ExportAttrs", False)
    fieldNames = None
    if writeAttrs:
      fieldNames = [field.name() for field in mapLayer.pendingFields()]

    hasLabel = False
    if writeAttrs:
      attIdx = properties.get("comboBox_Label", None)
      if attIdx is not None:
        widgetValues = properties.get("labelHeightWidget", {})
        lyr["l"] = {"i": attIdx, "ht": int(widgetValues.get("comboData", 0)), "v": float(widgetValues.get("editText", 0)) * mapTo3d.multiplierZ}
        hasLabel = True

    # write layer object
    writer.writeLayer(lyr, fieldNames)

    feat = Feature(writer, layer)

    # initialize symbol rendering
    mapLayer.rendererV2().startRender(renderer.rendererContext(), mapLayer.pendingFields() if apiChanged23 else mapLayer)

    request = QgsFeatureRequest()
    # features to export
    clipGeom = None
    if properties.get("radioButton_IntersectingFeatures", False):
      request.setFilterRect(layer.transform.transformBoundingBox(baseExtent.boundingBox(), QgsCoordinateTransform.ReverseTransform))
      if False and properties.get("checkBox_Clip"):   #TODO: clip with rotated rect
        rect = QgsRectangle(baseExtent)
        rect.scale(0.999999)    # clip with slightly smaller extent than map canvas extent
        clipGeom = QgsGeometry.fromRect(rect)
        #clipGeom = QgsGeometry.fromRect(canvas.extent())

    for f in mapLayer.getFeatures(request):
      #TODO: if rotated, check intersections with the rect
      feat.setQgsFeature(f, clipGeom)
      if feat.geom is None:
        continue

      # write geometry
      obj_mod.write(writer, layer, feat)   # writer.writeFeature(layer, feat, obj_mod)

      # stack attributes in writer
      if writeAttrs:
        writer.addAttributes(f.attributes())

    # write attributes
    if writeAttrs:
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
    c = map(float, [p["lineEdit_xmin"], p["lineEdit_ymin"], p["lineEdit_xmax"], p["lineEdit_ymax"]])
  except:
    return None

  # normalize
  ll = extent.normalizePoint(c[0], c[1])
  ur = extent.normalizePoint(c[2], c[3])

  quadtree = QuadTree()
  quadtree.buildTreeByRect(QgsRectangle(ll.x(), ll.y(), ur.x(), ur.y()), p["spinBox_Height"])
  return quadtree

def dummyProgress(progress=None, statusMsg=None):
  pass
