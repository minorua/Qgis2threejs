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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import os
import codecs
import datetime
import re

try:
  from osgeo import ogr
except ImportError:
  import ogr

import gdal2threejs
import qgis2threejstools as tools
from quadtree import *
from vectorobject import *
from propertyreader import DEMPropertyReader, VectorPropertyReader

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

class Point:
  def __init__(self, x, y, z=0):
    self.x = x
    self.y = y
    self.z = z

class MapTo3D:
  def __init__(self, mapCanvas, planeWidth=100, verticalExaggeration=1, verticalShift=0):
    # map canvas
    self.mapExtent = mapCanvas.extent()

    # 3d
    self.planeWidth = planeWidth
    self.planeHeight = planeWidth * mapCanvas.extent().height() / mapCanvas.extent().width()

    self.verticalExaggeration = verticalExaggeration
    self.verticalShift = verticalShift

    self.multiplier = planeWidth / mapCanvas.extent().width()
    self.multiplierZ = self.multiplier * verticalExaggeration

  def transform(self, x, y, z=0):
    extent = self.mapExtent
    return Point((x - extent.xMinimum()) * self.multiplier - self.planeWidth / 2,
                 (y - extent.yMinimum()) * self.multiplier - self.planeHeight / 2,
                 (z + self.verticalShift) * self.multiplierZ)

  def transformPoint(self, pt):
    return self.transform(pt.x, pt.y, pt.z)

class Feature:
  def __init__(self, layer=None, prop=None, f=None):
    self.layer = layer
    self.prop = prop
    self.f = f
    self.clearGeometry()

  def clearGeometry(self):
    self.pts = []
    self.lines = []
    self.polygons = []
    self.centroids = []

  def setQgsFeature(self, qFeat):
    self.f = qFeat

  def addPoint(self, point):
    self.pts.append(point)

  def addLine(self, line):
    self.lines.append(line)

  def addPolygon(self, polygon):
    self.polygons.append(polygon)

  def addCentroid(self, centroid):
    self.centroids.append(centroid)

  def pointsAsList(self):
    return map(lambda pt: [pt.x, pt.y, pt.z], self.pts)

  def linesAsList(self):
    l = []
    for line in self.lines:
      l.append(map(lambda pt: [pt.x, pt.y, pt.z], line))
    return l

  def polygonsAsList(self):
    p = []
    for boundaries in self.polygons:
      b = []
      for boundary in boundaries:
        b.append(map(lambda pt: [pt.x, pt.y, pt.z], boundary))
      p.append(b)
    return p

  def color(self):
    return self.prop.color(self.layer, self.f)

  def transparency(self):
    return self.prop.transparency(self.layer, self.f)

  def propValues(self):
    return self.prop.values(self.f)

class OutputContext:
  def __init__(self, templateName, templateType, mapTo3d, canvas, properties, dialog, objectTypeManager, localBrowsingMode=True):
    self.templateName = templateName
    self.templateType = templateType
    self.mapTo3d = mapTo3d
    self.canvas = canvas
    self.properties = properties
    self.dialog = dialog
    self.objectTypeManager = objectTypeManager
    self.localBrowsingMode = localBrowsingMode
    mapSettings = canvas.mapSettings() if apiChanged23 else canvas.mapRenderer()
    self.crs = mapSettings.destinationCrs()

    p = properties[ObjectTreeItem.ITEM_CONTROLS]
    if p is None:
      self.controls = QSettings().value("/Qgis2threejs/lastControls", "TrackballControls.js", type=unicode)
    else:
      self.controls = p["comboBox_Controls"]

    self.demLayerId = None
    if templateType == "sphere":
      return

    self.demLayerId = demLayerId = properties[ObjectTreeItem.ITEM_DEM]["comboBox_DEMLayer"]
    if demLayerId:
      layer = QgsMapLayerRegistry().instance().mapLayer(demLayerId)
      self.warp_dem = tools.MemoryWarpRaster(layer.source().encode("UTF-8"))
    else:
      self.warp_dem = tools.FlatRaster()

  # deprecated
  def setWarpDem(self, warp_dem):
    QMessageBox.information(None, "", "setWarpDem has been deprecated")
    self.warp_dem = warp_dem

class MaterialManager:

  MESH_LAMBERT = 0
  LINE_BASIC = 1
  WIREFRAME = 2
  MESH_LAMBERT_SMOOTH = 0
  MESH_LAMBERT_FLAT = 3

  ERROR_COLOR = "0"

  def __init__(self):
    self.materials = []

  def getMeshLambertIndex(self, color, transparency=0, doubleSide=False):
    return self.getIndex(self.MESH_LAMBERT, color, transparency, doubleSide)

  def getSmoothMeshLambertIndex(self, color, transparency=0, doubleSide=False):
    return self.getIndex(self.MESH_LAMBERT_SMOOTH, color, transparency, doubleSide)

  def getFlatMeshLambertIndex(self, color, transparency=0, doubleSide=False):
    return self.getIndex(self.MESH_LAMBERT_FLAT, color, transparency, doubleSide)

  def getLineBasicIndex(self, color, transparency=0):
    return self.getIndex(self.LINE_BASIC, color, transparency)

  def getWireframeIndex(self, color, transparency=0):
    return self.getIndex(self.WIREFRAME, color, transparency)

  def getIndex(self, type, color, transparency=0, doubleSide=False):
    if color[0:2] != "0x":
      color = self.ERROR_COLOR

    mat = (type, color, transparency, doubleSide)
    if mat in self.materials:
      return self.materials.index(mat)

    index = len(self.materials)
    self.materials.append(mat)
    return index

  def write(self, f):
    f.write("\n")
    for index, mat in enumerate(self.materials):
      m = {"type": mat[0], "c": mat[1]}
      transparency = mat[2]
      if transparency > 0:
        opacity = 1.0 - float(transparency) / 100
        m["o"] = opacity
      if mat[3]:
        m["ds"] = 1
      f.write("mat[{0}] = {1};\n".format(index, pyobj2js(m, quoteHex=False)))

class JSWriter:
  def __init__(self, htmlfilename, context):
    self.htmlfilename = htmlfilename
    self.context = context
    self.jsfile = None
    self.jsindex = -1
    self.jsfile_count = 0
    self.layerCount = 0
    self.currentLayerIndex = 0
    self.currentFeatureIndex = -1
    self.attrs = []
    self.materialManager = MaterialManager()
    #TODO: integrate OutputContext and JSWriter => ThreeJSExporter
    #TODO: written flag

  def setContext(self, context):
    self.context = context

  def openFile(self, newfile=False):
    if newfile:
      self.prepareNext()
    if self.jsindex == -1:
      jsfilename = os.path.splitext(self.htmlfilename)[0] + ".js"
    else:
      jsfilename = os.path.splitext(self.htmlfilename)[0] + "_%d.js" % self.jsindex
    self.jsfile = codecs.open(jsfilename, "w", "UTF-8")
    self.jsfile_count += 1

  def closeFile(self):
    if self.jsfile:
      self.jsfile.close()
      self.jsfile = None

  def write(self, data):
    if self.jsfile is None:
      self.openFile()
    self.jsfile.write(data)

  def writeWorldInfo(self):
    # write information for coordinates transformation
    extent = self.context.canvas.extent()
    mapTo3d = self.context.mapTo3d
    fmt = "world = new World([{0},{1},{2},{3}],{4},{5},{6});\n"
    self.write(fmt.format(extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum(),
                          mapTo3d.planeWidth, mapTo3d.verticalExaggeration, mapTo3d.verticalShift))

  def writeLayer(self, obj, fieldNames=None):
    self.currentLayerIndex = self.layerCount
    self.write("\n" + "lyr[{0}] = new MapLayer({1});\n".format(self.currentLayerIndex, pyobj2js(obj)))
    if fieldNames is not None:
      self.write(u"lyr[{0}].a = {1};\n".format(self.currentLayerIndex, pyobj2js(fieldNames)))
    self.layerCount += 1
    self.currentFeatureIndex = -1
    self.attrs = []
    return self.currentLayerIndex

  def writeFeature(self, f):
    self.currentFeatureIndex += 1
    self.write("lyr[{0}].f[{1}] = {2};\n".format(self.currentLayerIndex, self.currentFeatureIndex, pyobj2js(f)))

  def addAttributes(self, attrs):
    self.attrs.append(attrs)

  def writeAttributes(self):
    for index, attrs in enumerate(self.attrs):
      self.write(u"lyr[{0}].f[{1}].a = {2};\n".format(self.currentLayerIndex, index, pyobj2js(attrs, True)))

  def prepareNext(self):
    self.closeFile()
    self.jsindex += 1

  def options(self):
    options = []
    properties = self.context.properties
    world = properties[ObjectTreeItem.ITEM_WORLD] or {}
    if world.get("radioButton_Color", False):
      options.append("option.bgcolor = {0};".format(world.get("lineEdit_Color", 0)))

    return "\n".join(options)

  def scripts(self):
    filetitle = os.path.splitext(os.path.split(self.htmlfilename)[1])[0]
    if self.jsindex == -1:
      return '<script src="./%s.js"></script>' % filetitle
    return "\n".join(map(lambda x: '<script src="./%s_%s.js"></script>' % (filetitle, x), range(self.jsfile_count)))

def exportToThreeJS(htmlfilename, context, progress=None):
  mapTo3d = context.mapTo3d
  canvas = context.canvas
  extent = canvas.extent()
  if progress is None:
    progress = dummyProgress
  temp_dir = QDir.tempPath()

  #TODO: do in JSWriter?
  timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")
  if htmlfilename == "":
    htmlfilename = tools.temporaryOutputDir() + "/%s.html" % timestamp
  out_dir, filename = os.path.split(htmlfilename)
  if not QDir(out_dir).exists():
    QDir().mkpath(out_dir)

  # create JavaScript writer object
  writer = JSWriter(htmlfilename, context)
  writer.timestamp = timestamp

  # read configuration of the template
  templatePath = os.path.join(tools.templateDir(), context.templateName)
  templateConfig = tools.getTemplateConfig(templatePath)
  templateType = templateConfig.get("type", "plain")
  if templateType == "sphere":
    writer.openFile(False)
    # render texture for sphere and write it
    progress(5, "rendering texture...")
    writeSphereTexture(writer)
  else:
    # plain type
    demProperties = context.properties[ObjectTreeItem.ITEM_DEM]
    isSimpleMode = demProperties.get("radioButton_Simple", False)
    writer.openFile(not isSimpleMode)
    writer.writeWorldInfo()
    progress(5, "writing DEM...")

    # write primary DEM
    if isSimpleMode:
      writeSimpleDEM(writer, demProperties, progress)
    else:
      writeMultiResDEM(writer, demProperties, progress)
      writer.prepareNext()

    # write additional DEM(s)
    primaryDEMLayerId = demProperties["comboBox_DEMLayer"]
    for layerId, properties in context.properties[ObjectTreeItem.ITEM_OPTDEM].iteritems():
      if layerId != primaryDEMLayerId and properties.get("visible", False):
        writeSimpleDEM(writer, properties)

    progress(50, "writing vector data...")

    # write vector data
    writeVectors(writer)

  progress(80, "")

  # copy three.js files
  tools.copyThreejsFiles(out_dir, context.controls)

  # copy additional library files
  tools.copyLibraries(out_dir, templateConfig)

  # generate html file
  with codecs.open(templatePath, "r", "UTF-8") as f:
    html = f.read()

  filetitle = os.path.splitext(filename)[0]
  with codecs.open(htmlfilename, "w", "UTF-8") as f:
    f.write(html.replace("${title}", filetitle).replace("${controls}", '<script src="./threejs/%s"></script>' % context.controls).replace("${options}", writer.options()).replace("${scripts}", writer.scripts()))

  return htmlfilename

def writeSimpleDEM(writer, properties, progress=None):
  context = writer.context
  mapTo3d = context.mapTo3d
  canvas = context.canvas
  extent = canvas.extent()
  temp_dir = QDir.tempPath()
  timestamp = writer.timestamp
  htmlfilename = writer.htmlfilename
  if progress is None:
    progress = dummyProgress

  prop = DEMPropertyReader(properties)
  dem_width = prop.width()
  dem_height = prop.height()

  # warp dem
  # calculate extent. output dem should be handled as points.
  xres = extent.width() / (dem_width - 1)
  yres = extent.height() / (dem_height - 1)
  geotransform = [extent.xMinimum() - xres / 2, xres, 0, extent.yMaximum() + yres / 2, 0, -yres]
  wkt = str(context.crs.toWkt())

  layerName = ""
  demLayerId = properties["comboBox_DEMLayer"]
  if demLayerId:
    layer = QgsMapLayerRegistry().instance().mapLayer(demLayerId)
    layerName = layer.name()
    warp_dem = tools.MemoryWarpRaster(layer.source().encode("UTF-8"))
  else:
    warp_dem = tools.FlatRaster()
  # warp dem
  dem_values = warp_dem.read(dem_width, dem_height, wkt, geotransform)

  # calculate statistics
  stats = {"max": max(dem_values), "min": min(dem_values)}

  # shift and scale
  if mapTo3d.verticalShift != 0:
    dem_values = map(lambda x: x + mapTo3d.verticalShift, dem_values)
  if mapTo3d.multiplierZ != 1:
    dem_values = map(lambda x: x * mapTo3d.multiplierZ, dem_values)
  if debug_mode:
    qDebug("Warped DEM: %d x %d, extent %s" % (dem_width, dem_height, str(geotransform)))

  surroundings = properties.get("checkBox_Surroundings", False)
  if surroundings:
    roughenEdges(dem_width, dem_height, dem_values, properties["spinBox_Roughening"])

  # layer dict
  lyr = {"type": "dem", "name": layerName, "stats": stats}
  lyr["q"] = 1    #queryable
  dem = {"width": dem_width, "height": dem_height}
  dem["plane"] = {"width": mapTo3d.planeWidth, "height": mapTo3d.planeHeight, "offsetX": 0, "offsetY": 0}
  lyr["dem"] = [dem]

  # DEM transparency
  demTransparency = prop.properties["spinBox_demtransp"]

  # display type
  texData = texSrc = None
  if properties.get("radioButton_MapCanvas", False):
    # save map canvas image
    #TODO: prepare material(texture) in Material manager (result is tex -> material index)
    if 1:   #context.localBrowsingMode:
      texfilename = os.path.join(temp_dir, "tex%s.png" % (timestamp))
      canvas.saveAsImage(texfilename)
      texData = gdal2threejs.base64image(texfilename)
      tools.removeTemporaryFiles([texfilename, texfilename + "w"])
    else:
      #TODO: multiple DEMs output not in localBrowsingMode
      texfilename = os.path.splitext(htmlfilename)[0] + ".png"
      canvas.saveAsImage(texfilename)
      texSrc = os.path.split(texfilename)[1]
      tools.removeTemporaryFiles([texfilename + "w"])

  elif properties.get("radioButton_ImageFile", False):
    filename = properties.get("lineEdit_ImageFile", "")
    if os.path.exists(filename):
      texData = gdal2threejs.base64image(filename)
    else:
      texData = ""  #
      QgsMessageLog.logMessage(u'Image file not found: {0}'.format(filename), "Qgis2threejs")

  elif properties.get("radioButton_SolidColor", False):
    dem["m"] = writer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], demTransparency)

  elif properties.get("radioButton_Wireframe", False):
    dem["m"] = writer.materialManager.getWireframeIndex(properties["lineEdit_Color"], demTransparency)

  if texData is not None or texSrc is not None:
    tex = {}
    if texSrc is not None:
      tex["src"] = texSrc
    if demTransparency > 0:
      demOpacity = 1.0 - float(demTransparency) / 100
      tex["o"] = demOpacity
      tex["t"] = demOpacity < 1  #
    dem["t"] = tex

  if properties.get("checkBox_Shading", True):
    dem["shading"] = True

  if not surroundings and properties.get("checkBox_Sides", False):
    side = {}
    sidesTransparency = prop.properties["spinBox_sidetransp"]
    if sidesTransparency > 0:
      sidesOpacity = str(1.0 - float(sidesTransparency) / 100)
      side["o"] = sidesOpacity
    dem["s"] = side

  if not surroundings and properties.get("checkBox_Frame", False):
    dem["frame"] = True

  # write layer and central dem
  lyrIdx = writer.writeLayer(lyr)
  writer.write("lyr[{0}].dem[0].data = [{1}];\n".format(lyrIdx, ",".join(map(gdal2threejs.formatValue, dem_values))))
  if texData is not None:
    writer.write('lyr[{0}].dem[0].t.data = "{1}";\n'.format(lyrIdx, texData))

  # write surrounding dems
  if surroundings:
    writeSurroundingDEM(writer, lyrIdx, stats, properties, progress)
    # overwrite stats
    writer.write("lyr[{0}].stats = {1};\n".format(lyrIdx, pyobj2js(stats)))

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

def writeSurroundingDEM(writer, lyrIdx, stats, properties, progress=None):
  context = writer.context
  mapTo3d = context.mapTo3d
  canvas = context.canvas
  if progress is None:
    progress = dummyProgress
  demlayer = QgsMapLayerRegistry().instance().mapLayer(properties["comboBox_DEMLayer"])
  htmlfilename = writer.htmlfilename

  # options
  size = properties["spinBox_Size"]
  roughening = properties["spinBox_Roughening"]
  demTransparency = properties["spinBox_demtransp"]

  prop = DEMPropertyReader(properties)
  dem_width = (prop.width() - 1) / roughening + 1
  dem_height = (prop.height() - 1) / roughening + 1

  # create an image for texture
  image_basesize = 256
  hpw = canvas.extent().height() / canvas.extent().width()
  if hpw < 1:
    image_width = image_basesize
    image_height = round(image_width * hpw)
    #image_height = image_basesize * max(1, int(round(1 / hpw)))    # not rendered expectedly
  else:
    image_height = image_basesize
    image_width = round(image_height / hpw)
  image = QImage(image_width, image_height, QImage.Format_ARGB32_Premultiplied)

  layerids = []
  for layer in canvas.layers():
    layerids.append(unicode(layer.id()))

  # set up a renderer
  labeling = QgsPalLabeling()
  renderer = QgsMapRenderer()
  renderer.setOutputSize(image.size(), image.logicalDpiX())
  renderer.setDestinationCrs(context.crs)
  renderer.setProjectionsEnabled(True)
  renderer.setLabelingEngine(labeling)
  renderer.setLayerSet(layerids)

  painter = QPainter()
  antialias = True
  fillColor = canvas.canvasColor()
  if float(".".join(QT_VERSION_STR.split(".")[0:2])) < 4.8:
    fillColor = qRgb(fillColor.red(), fillColor.green(), fillColor.blue())

  warp_dem = tools.MemoryWarpRaster(demlayer.source().encode("UTF-8"))
  wkt = str(context.crs.toWkt())

  scripts = []
  plane_index = 1
  size2 = size * size
  for i in range(size2):
    progress(40 * i / size2 + 10)
    if i == (size2 - 1) / 2:    # center (map canvas)
      continue
    sx = i % size - (size - 1) / 2
    sy = i / size - (size - 1) / 2

    # calculate extent
    e = canvas.extent()
    extent = QgsRectangle(e.xMinimum() + sx * e.width(), e.yMinimum() + sy * e.height(),
                          e.xMaximum() + sx * e.width(), e.yMaximum() + sy * e.height())

    # calculate extent. output dem should be handled as points.
    xres = extent.width() / (dem_width - 1)
    yres = extent.height() / (dem_height - 1)
    geotransform = [extent.xMinimum() - xres / 2, xres, 0, extent.yMaximum() + yres / 2, 0, -yres]

    # warp dem
    dem_values = warp_dem.read(dem_width, dem_height, wkt, geotransform)
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
    if debug_mode:
      qDebug("Warped DEM: %d x %d, extent %s" % (dem_width, dem_height, str(geotransform)))

    # generate javascript data file
    planeWidth = mapTo3d.planeWidth * extent.width() / canvas.extent().width()
    planeHeight = mapTo3d.planeHeight * extent.height() / canvas.extent().height()
    offsetX = mapTo3d.planeWidth * (extent.xMinimum() - canvas.extent().xMinimum()) / canvas.extent().width() + planeWidth / 2 - mapTo3d.planeWidth / 2
    offsetY = mapTo3d.planeHeight * (extent.yMinimum() - canvas.extent().yMinimum()) / canvas.extent().height() + planeHeight / 2 - mapTo3d.planeHeight / 2
    dem = {"width": dem_width, "height": dem_height}
    dem["plane"] = {"width": planeWidth, "height": planeHeight, "offsetX": offsetX, "offsetY": offsetY}

    # display type
    texData = None
    if properties.get("radioButton_MapCanvas", False):
      renderer.setExtent(extent)
      # render map image
      image.fill(fillColor)
      painter.begin(image)
      if antialias:
        painter.setRenderHint(QPainter.Antialiasing)
      renderer.render(painter)
      painter.end()

      tex = {}
      if context.localBrowsingMode:
        texData = tools.base64image(image)
      else:
        texfilename = os.path.splitext(htmlfilename)[0] + "_%d.png" % plane_index
        image.save(texfilename)
        texSrc = os.path.split(texfilename)[1]
        tex["src"] = texSrc

      if demTransparency > 0:
        demOpacity = 1.0 - float(demTransparency) / 100
        tex["o"] = demOpacity
        tex["t"] = demOpacity < 1  #
      dem["t"] = tex

    elif properties.get("radioButton_SolidColor", False):
      dem["m"] = writer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], demTransparency)

    elif properties.get("radioButton_Wireframe", False):
      dem["m"] = writer.materialManager.getWireframeIndex(properties["lineEdit_Color"], demTransparency)

    if properties.get("checkBox_Shading", True):
      dem["shading"] = True

    # write dem object
    writer.write("lyr[{0}].dem[{1}] = {2};\n".format(lyrIdx, plane_index, pyobj2js(dem)))
    writer.write("lyr[{0}].dem[{1}].data = [{2}];\n".format(lyrIdx, plane_index, ",".join(map(gdal2threejs.formatValue, dem_values))))
    if texData is not None:
      writer.write('lyr[{0}].dem[{1}].t.data = "{2}";\n'.format(lyrIdx, plane_index, texData))
    plane_index += 1

def writeMultiResDEM(writer, properties, progress=None):
  context = writer.context
  mapTo3d = context.mapTo3d
  canvas = context.canvas
  if progress is None:
    progress = dummyProgress
  demlayer = QgsMapLayerRegistry().instance().mapLayer(properties["comboBox_DEMLayer"])
  temp_dir = QDir.tempPath()
  timestamp = writer.timestamp
  htmlfilename = writer.htmlfilename

  out_dir, filename = os.path.split(htmlfilename)
  filetitle = os.path.splitext(filename)[0]

  # material options
  demTransparency = properties["spinBox_demtransp"]

  # layer dict
  lyr = {"type": "dem", "name": demlayer.name(), "dem": []}
  lyr["q"] = 1    #queryable
  lyrIdx = writer.writeLayer(lyr)

  # create quad tree
  quadtree = createQuadTree(canvas.extent(), properties)
  if quadtree is None:
    QMessageBox.warning(None, "Qgis2threejs", "Focus point/area is not selected.")
    return
  quads = quadtree.quads()

  # create quads and a point on map canvas with rubber bands
  context.dialog.createRubberBands(quads, quadtree.focusRect.center())

  # create an image for texture
  image_basesize = 256
  hpw = canvas.extent().height() / canvas.extent().width()
  if hpw < 1:
    image_width = image_basesize
    image_height = round(image_width * hpw)
  else:
    image_height = image_basesize
    image_width = round(image_height / hpw)
  image = QImage(image_width, image_height, QImage.Format_ARGB32_Premultiplied)
  #qDebug("Created image size: %d, %d" % (image_width, image_height))

  layerids = []
  for layer in canvas.layers():
    layerids.append(unicode(layer.id()))

  # set up a renderer
  labeling = QgsPalLabeling()
  renderer = QgsMapRenderer()
  renderer.setOutputSize(image.size(), image.logicalDpiX())
  renderer.setDestinationCrs(context.crs)
  renderer.setProjectionsEnabled(True)
  renderer.setLabelingEngine(labeling)
  renderer.setLayerSet(layerids)

  painter = QPainter()
  antialias = True
  fillColor = canvas.canvasColor()
  if float(".".join(QT_VERSION_STR.split(".")[0:2])) < 4.8:
    fillColor = qRgb(fillColor.red(), fillColor.green(), fillColor.blue())

  # (currently) dem size should be 2 ^ quadtree.height * a + 1, where a is larger integer than 0
  # with smooth resolution change, this is not necessary
  dem_width = dem_height = max(64, 2 ** quadtree.height) + 1

  warp_dem = tools.MemoryWarpRaster(demlayer.source().encode("UTF-8"))
  wkt = str(context.crs.toWkt())

  unites_center = True
  centerQuads = DEMQuadList(dem_width, dem_height)
  scripts = []
  stats = None
  plane_index = 0
  for i, quad in enumerate(quads):
    progress(45 * i / len(quads) + 5)
    extent = quad.extent

    # calculate extent. output dem should be handled as points.
    xres = extent.width() / (dem_width - 1)
    yres = extent.height() / (dem_height - 1)
    geotransform = [extent.xMinimum() - xres / 2, xres, 0, extent.yMaximum() + yres / 2, 0, -yres]

    # warp dem
    dem_values = warp_dem.read(dem_width, dem_height, wkt, geotransform)
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
    if debug_mode:
      qDebug("Warped DEM: %d x %d, extent %s" % (dem_width, dem_height, str(geotransform)))

    # generate javascript data file
    planeWidth = mapTo3d.planeWidth * extent.width() / canvas.extent().width()
    planeHeight = mapTo3d.planeHeight * extent.height() / canvas.extent().height()
    offsetX = mapTo3d.planeWidth * (extent.xMinimum() - canvas.extent().xMinimum()) / canvas.extent().width() + planeWidth / 2 - mapTo3d.planeWidth / 2
    offsetY = mapTo3d.planeHeight * (extent.yMinimum() - canvas.extent().yMinimum()) / canvas.extent().height() + planeHeight / 2 - mapTo3d.planeHeight / 2

    # value resampling on edges for combination with different resolution DEM
    neighbors = quadtree.neighbors(quad)
    #qDebug("Output quad (%d %s): height=%d" % (i, str(quad), quad.height))
    for direction, neighbor in enumerate(neighbors):
      if neighbor is None:
        continue
      #qDebug(" neighbor %d %s: height=%d" % (direction, str(neighbor), neighbor.height))
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

    if quad.height < quadtree.height or unites_center == False:
      dem = {"width": dem_width, "height": dem_height}
      dem["plane"] = {"width": planeWidth, "height": planeHeight, "offsetX": offsetX, "offsetY": offsetY}

      # display type
      texData = None
      if properties.get("radioButton_MapCanvas", False):
        renderer.setExtent(extent)
        # render map image
        image.fill(fillColor)
        painter.begin(image)
        if antialias:
          painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter)
        painter.end()

        tex = {}
        if context.localBrowsingMode:
          texData = tools.base64image(image)
        else:
          texfilename = os.path.splitext(htmlfilename)[0] + "_%d.png" % plane_index
          image.save(texfilename)
          texSrc = os.path.split(texfilename)[1]
          tex["src"] = texSrc

        if demTransparency > 0:
          demOpacity = 1.0 - float(demTransparency) / 100
          tex["o"] = demOpacity
          tex["t"] = demOpacity < 1  #
        dem["t"] = tex

      elif properties.get("radioButton_SolidColor", False):
        dem["m"] = writer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], demTransparency)

      elif properties.get("radioButton_Wireframe", False):
        dem["m"] = writer.materialManager.getWireframeIndex(properties["lineEdit_Color"], demTransparency)

      if properties.get("checkBox_Shading", True):
        dem["shading"] = True

      # write dem object
      writer.openFile(True)
      writer.write("lyr[{0}].dem[{1}] = {2};\n".format(lyrIdx, plane_index, pyobj2js(dem)))
      writer.write("lyr[{0}].dem[{1}].data = [{2}];\n".format(lyrIdx, plane_index, ",".join(map(gdal2threejs.formatValue, dem_values))))
      if texData is not None:
        writer.write('lyr[{0}].dem[{1}].t.data = "{2}";\n'.format(lyrIdx, plane_index, texData))
      plane_index += 1
    else:
      centerQuads.addQuad(quad, dem_values)

  if unites_center:
    extent = centerQuads.extent()
    dem_width = (dem_width - 1) * centerQuads.width() + 1
    dem_height = (dem_height - 1) * centerQuads.height() + 1
    dem_values = centerQuads.unitedDEM()
    planeWidth = mapTo3d.planeWidth * extent.width() / canvas.extent().width()
    planeHeight = mapTo3d.planeHeight * extent.height() / canvas.extent().height()
    offsetX = mapTo3d.planeWidth * (extent.xMinimum() - canvas.extent().xMinimum()) / canvas.extent().width() + planeWidth / 2 - mapTo3d.planeWidth / 2
    offsetY = mapTo3d.planeHeight * (extent.yMinimum() - canvas.extent().yMinimum()) / canvas.extent().height() + planeHeight / 2 - mapTo3d.planeHeight / 2
    dem = {"width": dem_width, "height": dem_height}
    dem["plane"] = {"width": planeWidth, "height": planeHeight, "offsetX": offsetX, "offsetY": offsetY}

    # display type
    texData = None
    if properties.get("radioButton_MapCanvas", False):
      if hpw < 1:
        image_width = image_basesize * centerQuads.width()
        image_height = round(image_width * hpw)
      else:
        image_height = image_basesize * centerQuads.height()
        image_width = round(image_height / hpw)
      image = QImage(image_width, image_height, QImage.Format_ARGB32_Premultiplied)
      #qDebug("Created image size: %d, %d" % (image_width, image_height))

      renderer.setOutputSize(image.size(), image.logicalDpiX())
      renderer.setExtent(extent)

      # render map image
      image.fill(fillColor)
      painter.begin(image)
      if antialias:
        painter.setRenderHint(QPainter.Antialiasing)
      renderer.render(painter)
      painter.end()

      tex = {}
      if context.localBrowsingMode:
        texData = tools.base64image(image)
      else:
        texfilename = os.path.splitext(htmlfilename)[0] + "_%d.png" % plane_index
        image.save(texfilename)
        texSrc = os.path.split(texfilename)[1]
        tex["src"] = texSrc

      if demTransparency > 0:
        demOpacity = str(1.0 - float(demTransparency) / 100)
        tex["o"] = demOpacity
        tex["t"] = demOpacity < 1  #
      dem["t"] = tex

    elif properties.get("radioButton_SolidColor", False):
      dem["m"] = writer.materialManager.getMeshLambertIndex(properties["lineEdit_Color"], demTransparency)

    elif properties.get("radioButton_Wireframe", False):
      dem["m"] = writer.materialManager.getWireframeIndex(properties["lineEdit_Color"], demTransparency)

    # write dem object
    writer.openFile(True)
    writer.write("lyr[{0}].dem[{1}] = {2};\n".format(lyrIdx, plane_index, pyobj2js(dem)))
    writer.write("lyr[{0}].dem[{1}].data = [{2}];\n".format(lyrIdx, plane_index, ",".join(map(gdal2threejs.formatValue, dem_values))))
    if texData is not None:
      writer.write('lyr[{0}].dem[{1}].t.data = "{2}";\n'.format(lyrIdx, plane_index, texData))
    plane_index += 1

  writer.write("lyr[{0}].stats = {1};\n".format(lyrIdx, pyobj2js(stats)))

def writeVectors(writer):
  context = writer.context
  canvas = context.canvas
  mapTo3d = context.mapTo3d
  warp_dem = context.warp_dem
  renderer = QgsMapRenderer()

  layerProperties = {}
  for itemType in [ObjectTreeItem.ITEM_POINT, ObjectTreeItem.ITEM_LINE, ObjectTreeItem.ITEM_POLYGON]:
    for layerId, properties in context.properties[itemType].iteritems():
      if properties.get("visible", False):
        layerProperties[layerId] = properties

  for layerId, properties in layerProperties.iteritems():
    layer = QgsMapLayerRegistry().instance().mapLayer(layerId)
    if layer is None:
      continue
    geom_type = layer.geometryType()
    prop = VectorPropertyReader(context.objectTypeManager, layer, properties)
    obj_mod = context.objectTypeManager.module(prop.mod_index)
    if obj_mod is None:
      qDebug("Module not found")
      continue

    # write layer object
    lyr = {"name": layer.name(), "f": []}
    lyr["type"] = {QGis.Point: "point", QGis.Line: "line", QGis.Polygon: "polygon"}.get(geom_type, "")
    lyr["q"] = 1    #queryable
    lyr["objType"] = prop.type_name

    # make list of field names
    writeAttrs = properties.get("checkBox_ExportAttrs", False)
    fieldNames = None
    if writeAttrs:
      fieldNames = []
      fields = layer.pendingFields()
      for i in range(fields.count()):
        fieldNames.append(fields[i].name())

    hasLabel = False
    if writeAttrs:
      attIdx = properties.get("comboBox_Label", None)
      if attIdx is not None:
        labelHeight = properties.get("labelHeightWidget", [0] * 3)
        lyr["l"] = {"i": attIdx, "ht": int(labelHeight[0]), "v": float(labelHeight[2]) * mapTo3d.multiplierZ}
        hasLabel = True

    # wreite layer object
    writer.writeLayer(lyr, fieldNames)

    # initialize symbol rendering
    layer.rendererV2().startRender(renderer.rendererContext(), layer.pendingFields() if apiChanged23 else layer)

    feat = Feature(layer, prop)
    transform = QgsCoordinateTransform(layer.crs(), context.crs)
    wkt = str(context.crs.toWkt())
    request = QgsFeatureRequest().setFilterRect(transform.transformBoundingBox(canvas.extent(), QgsCoordinateTransform.ReverseTransform))
    for f in layer.getFeatures(request):
      feat.clearGeometry()
      feat.setQgsFeature(f)

      geom = f.geometry()
      geom_type == geom.type()
      wkb_type = geom.wkbType()
      if geom_type == QGis.Point:
        if prop.useZ():
          for point in pointsFromWkb25D(geom.asWkb()):
            pt = transform.transform(point[0], point[1])
            feat.addPoint(mapTo3d.transform(pt.x(), pt.y(), point[2] + prop.relativeHeight(f)))
          obj_mod.write(writer, feat)
        else:
          if geom.isMultipart():
            points = geom.asMultiPoint()
          else:
            points = [geom.asPoint()]

          for point in points:
            pt = transform.transform(point)
            if prop.isHeightRelativeToSurface():
              # get surface elevation at the point and relative height
              h = warp_dem.readValue(wkt, pt.x(), pt.y()) + prop.relativeHeight(f)
            else:
              h = prop.relativeHeight(f)
            feat.addPoint(mapTo3d.transform(pt.x(), pt.y(), h))
          obj_mod.write(writer, feat)

      elif geom_type == QGis.Line:
        if prop.useZ():
          for line in linesFromWkb25D(geom.asWkb()):
            points = []
            for point in line:
              pt = transform.transform(point[0], point[1])
              points.append(mapTo3d.transform(pt.x(), pt.y(), point[2] + prop.relativeHeight(f)))
            feat.addLine(points)
          obj_mod.write(writer, feat)
        else:
          if geom.isMultipart():
            lines = geom.asMultiPolyline()
          else:
            lines = [geom.asPolyline()]
          for line in lines:
            points = []
            for pt_orig in line:
              pt = transform.transform(pt_orig)
              if prop.isHeightRelativeToSurface():
                h = warp_dem.readValue(wkt, pt.x(), pt.y()) + prop.relativeHeight(f)
              else:
                h = prop.relativeHeight(f)
              points.append(mapTo3d.transform(pt.x(), pt.y(), h))
            feat.addLine(points)
          obj_mod.write(writer, feat)

      elif geom_type == QGis.Polygon:
        useCentroidHeight = True
        labelPerPolygon = True

        if geom.isMultipart():
          polygons = geom.asMultiPolygon()
        else:
          polygons = [geom.asPolygon()]

        if hasLabel and not labelPerPolygon:
          centroidHeight = 0
          pt = transform.transform(geom.centroid().asPoint())
          if prop.isHeightRelativeToSurface():
            centroidHeight = warp_dem.readValue(wkt, pt.x(), pt.y()) + prop.relativeHeight(f)
          else:
            centroidHeight = prop.relativeHeight(f)
          feat.addCentroid(mapTo3d.transform(pt.x(), pt.y(), centroidHeight))

        for polygon in polygons:
          if useCentroidHeight or hasLabel:
            centroidHeight = 0
            pt = transform.transform(QgsGeometry.fromPolygon(polygon).centroid().asPoint())
            if prop.isHeightRelativeToSurface():
              centroidHeight = warp_dem.readValue(wkt, pt.x(), pt.y()) + prop.relativeHeight(f)
            else:
              centroidHeight = prop.relativeHeight(f)
            if hasLabel and labelPerPolygon:
              feat.addCentroid(mapTo3d.transform(pt.x(), pt.y(), centroidHeight))

          boundaries = []
          points = []
          # outer boundary
          for pt_orig in polygon[0]:
            pt = transform.transform(pt_orig)
            if useCentroidHeight:
              h = centroidHeight
            elif prop.isHeightRelativeToSurface():
              h = warp_dem.readValue(wkt, pt.x(), pt.y()) + prop.relativeHeight(f)
            else:
              h = prop.relativeHeight(f)
            points.append(mapTo3d.transform(pt.x(), pt.y(), h))
          boundaries.append(points)
          # inner boundaries
          for inBoundary in polygon[1:]:
            points = []
            for pt_orig in inBoundary:
              pt = transform.transform(pt_orig)
              if useCentroidHeight:
                h = centroidHeight
              elif prop.isHeightRelativeToSurface():
                h = warp_dem.readValue(wkt, pt.x(), pt.y()) + prop.relativeHeight(f)
              else:
                h = prop.relativeHeight(f)
              points.append(mapTo3d.transform(pt.x(), pt.y(), h))
            points.reverse()    # to counter clockwise direction
            boundaries.append(points)
          feat.addPolygon(boundaries)
        obj_mod.write(writer, feat)

      # stack attributes in writer
      if writeAttrs:
        writer.addAttributes(f.attributes())
    # write attributes
    if writeAttrs:
      writer.writeAttributes()

    layer.rendererV2().stopRender(renderer.rendererContext())

  # write materials
  writer.materialManager.write(writer)

def writeSphereTexture(writer):
  #context = writer.context
  canvas = writer.context.canvas
  antialias = True

  image_width = 1024
  image_height = 512
  image = QImage(image_width, image_height, QImage.Format_ARGB32_Premultiplied)

  # fill image with canvas color
  fillColor = canvas.canvasColor()
  if float(".".join(QT_VERSION_STR.split(".")[0:2])) < 4.8:
    fillColor = qRgb(fillColor.red(), fillColor.green(), fillColor.blue())
  image.fill(fillColor)

  # set up a renderer
  renderer = QgsMapRenderer()
  renderer.setOutputSize(image.size(), image.logicalDpiX())

  crs = QgsCoordinateReferenceSystem(4326)
  renderer.setDestinationCrs(crs)
  renderer.setProjectionsEnabled(True)

  layerids = []
  for layer in canvas.layers():
    layerids.append(unicode(layer.id()))
  renderer.setLayerSet(layerids)

  extent = QgsRectangle(-180, -90, 180, 90)
  renderer.setExtent(extent)

  # render map image
  painter = QPainter()
  painter.begin(image)
  if antialias:
    painter.setRenderHint(QPainter.Antialiasing)
  renderer.render(painter)
  painter.end()

  #if context.localBrowsingMode:
  texData = tools.base64image(image)
  writer.write('tex = "{0}";\n'.format(texData))

def pointsFromWkb25D(wkb):
  geom25d = ogr.CreateGeometryFromWkb(wkb)
  geomType = geom25d.GetGeometryType()
  geoms = []
  if geomType == ogr.wkbPoint25D:
    geoms = [geom25d]
  elif geomType == ogr.wkbMultiPoint25D:
    for i in range(geom25d.GetGeometryCount()):
      geoms.append(geom25d.GetGeometryRef(i))
  pts = []
  for geom in geoms:
    if hasattr(geom, "GetPoints"):
      pts += geom.GetPoints()
    else:
      for i in range(geom.GetPointCount()):
        pts.append(geom.GetPoint(i))
  return pts

def linesFromWkb25D(wkb):
  geom25d = ogr.CreateGeometryFromWkb(wkb)
  geomType = geom25d.GetGeometryType()
  geoms = []
  if geomType == ogr.wkbLineString25D:
    geoms = [geom25d]
  elif geomType == ogr.wkbMultiLineString25D:
    for i in range(geom25d.GetGeometryCount()):
      geoms.append(geom25d.GetGeometryRef(i))
  lines = []
  for geom in geoms:
    if hasattr(geom, "GetPoints"):
      pts = geom.GetPoints()
    else:
      pts = []
      for i in range(geom.GetPointCount()):
        pts.append(geom.GetPoint(i))
    lines.append(pts)
  return lines

def pyobj2js(obj, escape=False, quoteHex=True):
  if isinstance(obj, dict):
    items = []
    for k, v in obj.iteritems():
      items.append("{0}:{1}".format(k, pyobj2js(v, escape, quoteHex)))
    return "{" + ",".join(items) + "}"
  elif isinstance(obj, list):
    items = []
    for v in obj:
      items.append(unicode(pyobj2js(v, escape, quoteHex)))
    return "[" + ",".join(items) + "]"
  elif isinstance(obj, bool):
    return "true" if obj else "false"
  elif isinstance(obj, (str, unicode)):
    if escape:
      return '"' + obj.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if not quoteHex and re.match("0x[0-9A-Fa-f]+$", obj):
      return obj
    return '"' + obj + '"'
  elif isinstance(obj, (int, float)):
    return obj
  return '"' + str(obj) + '"'

# createQuadTree(extent, demProperties)
def createQuadTree(extent, p):
  try:
    c = map(float, [p["lineEdit_xmin"], p["lineEdit_ymin"], p["lineEdit_xmax"], p["lineEdit_ymax"]])
  except:
    return None
  quadtree = QuadTree(extent)
  quadtree.buildTreeByRect(QgsRectangle(c[0], c[1], c[2], c[3]), p["spinBox_Height"])
  return quadtree

def dummyProgress(progress, statusMsg=None):
  pass
