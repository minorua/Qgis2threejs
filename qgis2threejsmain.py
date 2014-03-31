# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
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

try:
  from osgeo import ogr
except ImportError:
  import ogr

import gdal2threejs
import qgis2threejstools as tools
from quadtree import *
from vectorobject import *

apiChanged22 = False

class Point:
  def __init__(self, x, y, z=0):
    self.x = x
    self.y = y
    self.z = z

class MapTo3D:
  def __init__(self, mapCanvas, planeWidth=100, verticalExaggeration=1, verticalShift=0):
    # map canvas
    #self.canvasWidth, self.canvasHeight
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

class OutputContext:
  def __init__(self, templateName, controls, mapTo3d, canvas, demlayerid, vectorPropertiesDict, objectTypeManager, localBrowsingMode=True, dem_width=0, dem_height=0, side_transparency=0, dem_transparency=0):
    self.templateName = templateName
    self.controls = controls
    self.mapTo3d = mapTo3d
    self.canvas = canvas
    self.demlayerid = demlayerid
    self.vectorPropertiesDict = vectorPropertiesDict
    self.objectTypeManager = objectTypeManager
    self.localBrowsingMode = localBrowsingMode
    self.dem_width = dem_width
    self.dem_height = dem_height
    self.side_transparency = side_transparency
    self.dem_transparency = dem_transparency
    mapSettings = canvas.mapSettings() if apiChanged22 else canvas.mapRenderer()
    self.crs = mapSettings.destinationCrs()

  def setWarpDem(self, warp_dem):
    self.warp_dem = warp_dem

class MaterialManager:
  def __init__(self):
    self.ids = []
    self.materials = []

  def getMeshLambertIndex(self, color):
    return self.getIndex("ML" + color, "new THREE.MeshLambertMaterial({{color:{0},ambient:{0}}})".format(color))

  def getLineBasicIndex(self, color):
    return self.getIndex("LB" + color, "new THREE.LineBasicMaterial({{color:{0}}})".format(color))

  def getIndex(self, id, material):
    if id in self.ids:
      return self.ids.index(id)
    else:
      index = len(self.ids)
      self.ids.append(id)
      self.materials.append(material)
      return index

  def write(self, f):
    for index, material in enumerate(self.materials):
      f.write("mat[{0}] = {1};\n".format(index, material))

class JSWriter:
  def __init__(self, htmlfilename, context):
    self.htmlfilename = htmlfilename
    self.context = context
    self.jsfile = None
    self.jsindex = -1
    self.jsfile_count = 0
    self.materialManager = MaterialManager()

  def setContext(self, context):
    self.context = context

  def openFile(self, newfile=False):
    if newfile:
      self.prepareNext()
    if self.jsindex == -1:
      jsfilename = os.path.splitext(self.htmlfilename)[0] + ".js"
    else:
      jsfilename = os.path.splitext(self.htmlfilename)[0] + "_%d.js" % self.jsindex
    self.jsfile = open(jsfilename, "w")
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
    args = (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum(), mapTo3d.planeWidth, mapTo3d.verticalExaggeration, mapTo3d.verticalShift)
    lines = []
    lines.append("world = {mapExtent:[%f,%f,%f,%f],width:%f,zExaggeration:%f,zShift:%f};" % args)
    lines.append("world.height = world.width * (world.mapExtent[3] - world.mapExtent[1]) / (world.mapExtent[2] - world.mapExtent[0]);")
    lines.append("world.scale = world.width / (world.mapExtent[2] - world.mapExtent[0]);")
    lines.append("world.zScale = world.scale * world.zExaggeration;")
    self.write("\n".join(lines) + "\n")

  def prepareNext(self):
    self.closeFile()
    self.jsindex += 1

  def options(self):
    options = []
    if self.context.side_transparency == 100:
      options.append('option["nosides"] = true;')
    elif self.context.side_transparency > 0:
      options.append('option["side_opacity"] = %s;' % str(1.0 - float(self.context.side_transparency) / 100))
    if self.context.dem_transparency > 0:
      options.append('option["dem_opacity"] = %s;' % str(1.0 - float(self.context.dem_transparency) / 100))
    return "\n".join(options)

  def scripts(self):
    filetitle = os.path.splitext(os.path.split(self.htmlfilename)[1])[0]
    if self.jsindex == -1:
      return '<script src="./%s.js"></script>' % filetitle
    return "\n".join(map(lambda x: '<script src="./%s_%s.js"></script>' % (filetitle, x), range(self.jsfile_count)))

def runSimple(htmlfilename, context, progress=None):
  mapTo3d = context.mapTo3d
  canvas = context.canvas
  extent = canvas.extent()
  if progress is None:
    progress = dummyProgress
  temp_dir = QDir.tempPath()
  timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

  if htmlfilename == "":
    htmlfilename = tools.temporaryOutputDir() + "/%s.html" % timestamp
  out_dir, filename = os.path.split(htmlfilename)
  if not QDir(out_dir).exists():
    QDir().mkpath(out_dir)

  filetitle = os.path.splitext(filename)[0]

  # save map canvas image
  if context.localBrowsingMode:
    texfilename = os.path.join(temp_dir, "tex%s.png" % (timestamp))
    canvas.saveAsImage(texfilename)
    tex = gdal2threejs.base64image(texfilename)
    tools.removeTemporaryFiles([texfilename, texfilename + "w"])
  else:
    texfilename = os.path.splitext(htmlfilename)[0] + ".png"
    canvas.saveAsImage(texfilename)
    tex = os.path.split(texfilename)[1]
    tools.removeTemporaryFiles([texfilename + "w"])
  progress(20)

  # warp dem
  # calculate extent. output dem should be handled as points.
  xres = extent.width() / (context.dem_width - 1)
  yres = extent.height() / (context.dem_height - 1)
  geotransform = [extent.xMinimum() - xres / 2, xres, 0, extent.yMaximum() + yres / 2, 0, -yres]
  wkt = str(context.crs.toWkt())

  if context.demlayerid:
    demlayer = QgsMapLayerRegistry().instance().mapLayer(context.demlayerid)
    warp_dem = tools.MemoryWarpRaster(demlayer.source().encode("UTF-8"))
  else:
    warp_dem = tools.FlatRaster()

  dem_values = warp_dem.read(context.dem_width, context.dem_height, wkt, geotransform)
  #TODO: mapTo3d.verticalShift
  if mapTo3d.multiplierZ != 1:
    dem_values = map(lambda x: x * mapTo3d.multiplierZ, dem_values)
  if debug_mode:
    qDebug("Warped DEM: %d x %d, extent %s" % (context.dem_width, context.dem_height, str(geotransform)))
  context.setWarpDem(warp_dem)

  # create JavaScript writer object
  writer = JSWriter(htmlfilename, context)
  writer.openFile()
  writer.writeWorldInfo()

  # write dem data
  offsetX = offsetY = 0
  opt = "{width:%f,height:%f,offsetX:%f,offsetY:%f}" % (mapTo3d.planeWidth, mapTo3d.planeHeight, offsetX, offsetY)
  writer.write('dem[0] = {width:%d,height:%d,multiplierZ:%s,plane:%s,data:[%s]};\n' %
               (context.dem_width, context.dem_height, mapTo3d.multiplierZ, opt, ",".join(map(gdal2threejs.formatValue, dem_values))))
  writer.write('tex[0] = "%s";\n' % tex)
  progress(50)

  # write vector data
  writeVectors(writer)
  progress(80)

  # copy three.js files
  tools.copyThreejsFiles(out_dir, context.controls)

  # copy additional library files
  templatePath = os.path.join(tools.templateDir(), context.templateName)
  metadata = tools.getTemplateMetadata(templatePath)
  tools.copyLibraries(out_dir, metadata)

  # generate html file
  with codecs.open(templatePath, "r", "UTF-8") as f:
    html = f.read()

  with codecs.open(htmlfilename, "w", "UTF-8") as f:
    f.write(html.replace("${title}", filetitle).replace("${controls}", '<script src="./threejs/%s"></script>' % context.controls).replace("${options}", writer.options()).replace("${scripts}", writer.scripts()))

  return htmlfilename

def runAdvanced(htmlfilename, context, dialog, progress=None):
  mapTo3d = context.mapTo3d
  canvas = context.canvas
  if progress is None:
    progress = dummyProgress
  demlayer = QgsMapLayerRegistry().instance().mapLayer(context.demlayerid)
  temp_dir = QDir.tempPath()
  timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

  if htmlfilename == "":
    htmlfilename = tools.temporaryOutputDir() + "/%s.html" % timestamp
  out_dir, filename = os.path.split(htmlfilename)
  if not QDir(out_dir).exists():
    QDir().mkpath(out_dir)
  filetitle = os.path.splitext(filename)[0]

  # create quad tree
  quadtree = dialog.createQuadTree()
  if quadtree is None:
    QMessageBox.warning(None, "Qgis2threejs", "Focus point/area is not selected.")
    return
  quads = quadtree.quads()

  # create quads and a point on map canvas with rubber bands
  dialog.createRubberBands(quads, quadtree.focusRect.center())

  # create an image for texture
  image_basesize = 128
  hpw = canvas.extent().height() / canvas.extent().width()
  if hpw < 1:
    image_width = image_basesize
    image_height = round(image_width * hpw)
  else:
    image_height = image_basesize
    image_width = round(image_height * hpw)
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

  # create JavaScript writer object
  context.setWarpDem(warp_dem)
  writer = JSWriter(htmlfilename, context)
  writer.openFile(True)
  writer.writeWorldInfo()

  unites_center = True
  centerQuads = DEMQuadList(dem_width, dem_height)
  scripts = []
  plane_index = 0
  for i, quad in enumerate(quads):
    progress(50 * i / len(quads))
    extent = quad.extent

    if quad.height < quadtree.height or unites_center == False:
      renderer.setExtent(extent)
      # render map image
      image.fill(fillColor)
      painter.begin(image)
      if antialias:
        painter.setRenderHint(QPainter.Antialiasing)
      renderer.render(painter)
      painter.end()

      if context.localBrowsingMode:
        tex = tools.base64image(image)
      else:
        texfilename = os.path.splitext(htmlfilename)[0] + "_%d.png" % plane_index
        image.save(texfilename)
        tex = os.path.split(texfilename)[1]

    # calculate extent. output dem should be handled as points.
    xres = extent.width() / (dem_width - 1)
    yres = extent.height() / (dem_height - 1)
    geotransform = [extent.xMinimum() - xres / 2, xres, 0, extent.yMaximum() + yres / 2, 0, -yres]

    # warp dem
    dem_values = warp_dem.read(dem_width, dem_height, wkt, geotransform)
    #TODO: mapTo3d.verticalShift
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
      writer.openFile(True)
      opt = "{width:%f,height:%f,offsetX:%f,offsetY:%f}" % (planeWidth, planeHeight, offsetX, offsetY)
      writer.write('dem[%d] = {width:%d,height:%d,plane:%s,data:[%s]};\n' % (plane_index, dem_width, dem_height, opt, ",".join(map(gdal2threejs.formatValue, dem_values))))
      writer.write('tex[%d] = "%s";\n' % (plane_index, tex))
      plane_index += 1
    else:
      centerQuads.addQuad(quad, dem_values)

  if unites_center:
    extent = centerQuads.extent()
    if hpw < 1:
      image_width = image_basesize * centerQuads.width()
      image_height = round(image_width * hpw)
    else:
      image_height = image_basesize * centerQuads.height()
      image_width = round(image_height * hpw)
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

    if context.localBrowsingMode:
      tex = tools.base64image(image)
    else:
      texfilename = os.path.splitext(htmlfilename)[0] + "_%d.png" % plane_index
      image.save(texfilename)
      tex = os.path.split(texfilename)[1]

    dem_values = centerQuads.unitedDEM()
    planeWidth = mapTo3d.planeWidth * extent.width() / canvas.extent().width()
    planeHeight = mapTo3d.planeHeight * extent.height() / canvas.extent().height()
    offsetX = mapTo3d.planeWidth * (extent.xMinimum() - canvas.extent().xMinimum()) / canvas.extent().width() + planeWidth / 2 - mapTo3d.planeWidth / 2
    offsetY = mapTo3d.planeHeight * (extent.yMinimum() - canvas.extent().yMinimum()) / canvas.extent().height() + planeHeight / 2 - mapTo3d.planeHeight / 2

    dem_width = (dem_width - 1) * centerQuads.width() + 1
    dem_height = (dem_height - 1) * centerQuads.height() + 1

    writer.openFile(True)
    opt = "{width:%f,height:%f,offsetX:%f,offsetY:%f}" % (planeWidth, planeHeight, offsetX, offsetY)
    writer.write('dem[%d] = {width:%d,height:%d,plane:%s,data:[%s]};\n' % (plane_index, dem_width, dem_height, opt, ",".join(map(gdal2threejs.formatValue, dem_values))))
    writer.write('tex[%d] = "%s";\n' % (plane_index, tex))
    plane_index += 1
  progress(50)

  # vector data output
  writer.prepareNext()
  writeVectors(writer)
  progress(80)

  # copy three.js files
  tools.copyThreejsFiles(out_dir, context.controls)

  # copy additional library files
  templatePath = os.path.join(tools.templateDir(), context.templateName)
  metadata = tools.getTemplateMetadata(templatePath)
  tools.copyLibraries(out_dir, metadata)

  # generate html file
  with codecs.open(templatePath, "r", "UTF-8") as f:
    html = f.read()

  with codecs.open(htmlfilename, "w", "UTF-8") as f:
    f.write(html.replace("${title}", filetitle).replace("${controls}", '<script src="./threejs/%s"></script>' % context.controls).replace("${options}", writer.options()).replace("${scripts}", writer.scripts()))

  return htmlfilename

def writeVectors(writer):
  context = writer.context
  canvas = context.canvas
  mapTo3d = context.mapTo3d
  warp_dem = context.warp_dem
  for layerid, prop_dict in context.vectorPropertiesDict.items():
    properties = VectorObjectProperties(prop_dict)
    if not properties.visible:
      continue
    layer = QgsMapLayerRegistry().instance().mapLayer(layerid)
    if layer is None:
      continue
    geom_type = layer.geometryType()
    obj_mod = context.objectTypeManager.module(properties.mod_index)
    if obj_mod is None:
      qDebug("Module not found")
      continue
    transform = QgsCoordinateTransform(layer.crs(), context.crs)
    wkt = str(context.crs.toWkt())
    request = QgsFeatureRequest().setFilterRect(transform.transformBoundingBox(canvas.extent(), QgsCoordinateTransform.ReverseTransform))
    for f in layer.getFeatures(request):
      geom = f.geometry()
      geom_type == geom.type()
      wkb_type = geom.wkbType()
      if geom_type == QGis.Point:
        if properties.useZ():
          for pt in pointsFromWkb25D(geom.asWkb(), transform):
            h = pt[2] + properties.relativeHeight(f)
            obj_mod.write(writer, mapTo3d.transform(pt[0], pt[1], h), properties, layer, f)
        else:
          if geom.isMultipart():
            points = geom.asMultiPoint()
          else:
            points = [geom.asPoint()]
          for point in points:
            pt = transform.transform(point)
            if properties.isHeightRelativeToSurface():
              # get surface elevation at the point and relative height
              h = warp_dem.readValue(wkt, pt.x(), pt.y()) + properties.relativeHeight(f)
            else:
              h = properties.relativeHeight(f)
            obj_mod.write(writer, mapTo3d.transform(pt.x(), pt.y(), h), properties, layer, f)
      elif geom_type == QGis.Line:
        if properties.useZ():
          for line in linesFromWkb25D(geom.asWkb(), transform):
            points = []
            for pt in line:
              h = pt[2] + properties.relativeHeight(f)
              points.append(mapTo3d.transform(pt[0], pt[1], h))
            obj_mod.write(writer, points, properties, layer, f)
        else:
          if geom.isMultipart():
            lines = geom.asMultiPolyline()
          else:
            lines = [geom.asPolyline()]
          for line in lines:
            points = []
            for pt_orig in line:
              pt = transform.transform(pt_orig)
              if properties.isHeightRelativeToSurface():
                h = warp_dem.readValue(wkt, pt.x(), pt.y()) + properties.relativeHeight(f)
              else:
                h = properties.relativeHeight(f)
              points.append(mapTo3d.transform(pt.x(), pt.y(), h))
            obj_mod.write(writer, points, properties, layer, f)
      elif geom_type == QGis.Polygon:
        if geom.isMultipart():
          polygons = geom.asMultiPolygon()
        else:
          polygons = [geom.asPolygon()]

        useCentroidHeight = False
        if useCentroidHeight:
          pt = transform.transform(geom.centroid().asPoint())
          if properties.isHeightRelativeToSurface():
            centroidHeight = warp_dem.readValue(wkt, pt.x(), pt.y()) + properties.relativeHeight(f)
          else:
            centroidHeight = properties.relativeHeight(f)

        for polygon in polygons:
          boundaries = []
          points = []
          # outer boundary
          for pt_orig in polygon[0]:
            pt = transform.transform(pt_orig)
            if useCentroidHeight:
              h = centroidHeight
            elif properties.isHeightRelativeToSurface():
              h = warp_dem.readValue(wkt, pt.x(), pt.y()) + properties.relativeHeight(f)
            else:
              h = properties.relativeHeight(f)
            points.append(mapTo3d.transform(pt.x(), pt.y(), h))
          boundaries.append(points)
          # inner boundaries
          for inBoundary in polygon[1:]:
            points = []
            for pt_orig in inBoundary:
              pt = transform.transform(pt_orig)
              if useCentroidHeight:
                h = centroidHeight
              elif properties.isHeightRelativeToSurface():
                h = warp_dem.readValue(wkt, pt.x(), pt.y()) + properties.relativeHeight(f)
              else:
                h = properties.relativeHeight(f)
              points.append(mapTo3d.transform(pt.x(), pt.y(), h))
            points.reverse()    # to counter clockwise direction
            boundaries.append(points)
          obj_mod.write(writer, boundaries, properties, layer, f)
  # write materials
  writer.materialManager.write(writer)

def pointsFromWkb25D(wkb, transform):
  geom25d = ogr.CreateGeometryFromWkb(wkb)
  geomType = geom25d.GetGeometryType()
  geoms = []
  if geomType == ogr.wkbPoint25D:
    geoms = [geom25d]
  elif geomType == ogr.wkbMultiPoint25D:
    for i in range(geom25d.GetGeometryCount()):
      geoms.append(geom25d.GetGeometryRef(i))
  points = []
  for geom in geoms:
    if hasattr(geom, "GetPoints"):
      pts = geom.GetPoints()
    else:
      pts = []
      for i in range(geom.GetPointCount()):
        pts.append(geom.GetPoint(i))
    for pt_orig in pts:
      pt = transform.transform(pt_orig[0], pt_orig[1])
      points.append([pt.x(), pt.y(), pt_orig[2]])
  return points

def linesFromWkb25D(wkb, transform):
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
    points = []
    for pt_orig in pts:
      pt = transform.transform(pt_orig[0], pt_orig[1])
      points.append([pt.x(), pt.y(), pt_orig[2]])
    lines.append(points)
  return lines

def dummyProgress(progress):
  pass
