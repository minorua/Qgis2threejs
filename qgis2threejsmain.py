# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
                              -------------------
        begin                : 2014-01-16
        copyright            : (C) 2014 by Minoru Akagi
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
  def __init__(self, mapCanvas, planeWidth=100, verticalExaggeration=1):
    # map canvas
    #self.canvasWidth, self.canvasHeight
    self.mapExtent = mapCanvas.extent()

    # 3d
    self.planeWidth = planeWidth
    self.planeHeight = planeWidth * mapCanvas.extent().height() / mapCanvas.extent().width()

    self.verticalExaggeration = verticalExaggeration
    self.multiplier = planeWidth / mapCanvas.extent().width()
    self.multiplierZ = self.multiplier * verticalExaggeration

  def transform(self, x, y, z=0):
    extent = self.mapExtent
    return Point((x - extent.xMinimum()) * self.multiplier - self.planeWidth / 2,
                 (y - extent.yMinimum()) * self.multiplier - self.planeHeight / 2,
                 z * self.multiplierZ)

  def transformPoint(self, pt):
    return self.transform(pt.x, pt.y, pt.z)

class OutputContext:
  def __init__(self, mapTo3d, canvas, demlayerid, vectorPropertiesDict, objectTypeManager, localBrowsingMode=True, dem_width=0, dem_height=0):
    self.mapTo3d = mapTo3d
    self.canvas = canvas
    self.demlayerid = demlayerid
    self.vectorPropertiesDict = vectorPropertiesDict
    self.objectTypeManager = objectTypeManager
    self.localBrowsingMode = localBrowsingMode
    self.dem_width = dem_width
    self.dem_height = dem_height
    mapSettings = canvas.mapSettings() if apiChanged22 else canvas.mapRenderer()
    self.crs = mapSettings.destinationCrs()

  def setWarpDem(self, warp_dem):
    self.warp_dem = warp_dem

class JSWriter:
  def __init__(self, htmlfilename, context):
    self.htmlfilename = htmlfilename
    self.context = context
    self.jsfile = None
    self.jsindex = -1
    self.jsfile_count = 0

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

  def prepareNext(self):
    self.closeFile()
    self.jsindex += 1

  def scripts(self):
    filetitle = os.path.splitext(os.path.split(self.htmlfilename)[1])[0]
    if self.jsindex == -1:
      return '<script src="./%s.js"></script>' % filetitle
    return "\n".join(map(lambda x: '<script src="./%s_%s.js"></script>' % (filetitle, x), range(self.jsfile_count)))

def runSimple(htmlfilename, context, progress=None):
  mapTo3d = context.mapTo3d
  canvas = context.canvas
  extent = canvas.extent()
  demlayer = QgsMapLayerRegistry().instance().mapLayer(context.demlayerid)
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

  warp_dem = tools.MemoryWarpRaster(demlayer.source().encode("UTF-8"))
  dem_values = warp_dem.read(context.dem_width, context.dem_height, wkt, geotransform)
  if mapTo3d.multiplierZ != 1:
    dem_values = map(lambda x: x * mapTo3d.multiplierZ, dem_values)
  if debug_mode:
    qDebug("Warped DEM: %d x %d, extent %s" % (context.dem_width, context.dem_height, str(geotransform)))

  # create JavaScript writer object
  context.setWarpDem(warp_dem)
  writer = JSWriter(htmlfilename, context)
  writer.openFile()

  # write dem data
  offsetX = offsetY = 0
  opt = "{width:%f,height:%f,offsetX:%f,offsetY:%f}" % (mapTo3d.planeWidth, mapTo3d.planeHeight, offsetX, offsetY)
  writer.write('dem[0] = {width:%d,height:%d,plane:%s,data:[%s]};\n' % (context.dem_width, context.dem_height, opt, ",".join(map(gdal2threejs.formatValue, dem_values))))
  writer.write('tex[0] = "%s";\n' % tex)
  progress(50)

  # write vector data
  writeVectors(writer)
  progress(80)

  # copy files from template
  tools.copyThreejsFiles(out_dir)

  # generate html file
  with codecs.open(tools.pluginDir() + "/template.html", "r", "UTF-8") as f:
    html = f.read()

  with codecs.open(htmlfilename, "w", "UTF-8") as f:
    f.write(html.replace("${title}", filetitle).replace("${scripts}", writer.scripts()))

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

  # copy files from template
  tools.copyThreejsFiles(out_dir)

  # generate html file
  with codecs.open(tools.pluginDir() + "/template.html", "r", "UTF-8") as f:
    html = f.read()

  with codecs.open(htmlfilename, "w", "UTF-8") as f:
    f.write(html.replace("${title}", filetitle).replace("${scripts}", writer.scripts()))

  return htmlfilename

def writeVectors(writer):
  context = writer.context
  canvas = context.canvas
  mapTo3d = context.mapTo3d
  warp_dem = context.warp_dem
  tcolors = []
  materials = []
  for layerid, prop_dict in context.vectorPropertiesDict.items():
    properties = VectorObjectProperties(prop_dict)
    if not properties.visible:
      continue
    layer = QgsMapLayerRegistry().instance().mapLayer(layerid)
    geom_type = layer.geometryType()
    obj_mod = context.objectTypeManager.module(geom_type, properties.type_index)
    if obj_mod is None:
      qDebug("Module not found")
      continue
    transform = QgsCoordinateTransform(layer.crs(), context.crs)
    wkt = str(context.crs.toWkt())
    request = QgsFeatureRequest().setFilterRect(transform.transformBoundingBox(canvas.extent(), QgsCoordinateTransform.ReverseTransform))
    for f in layer.getFeatures(request):
      geom = f.geometry()
      geom_type == geom.type()
      color = properties.color(layer, f)
      tcolor = str(geom_type) + color
      if tcolor in tcolors:
        material_index = tcolors.index(tcolor)
      else:
        material_index = len(materials)
        if geom_type == QGis.Point or geom_type == QGis.Polygon:
          materials.append("mat[{0}] = new THREE.MeshLambertMaterial({{color:{1},ambient:{1}}});".format(material_index, color))
        elif geom_type == QGis.Line:
          materials.append("mat[{0}] = new THREE.LineBasicMaterial({{color:{1}}});".format(material_index, color))
        tcolors.append(tcolor)

      if geom_type == QGis.Point:
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
          obj_mod.write(writer, mapTo3d.transform(pt.x(), pt.y(), h), material_index, properties, f)
      elif geom_type == QGis.Line:
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
          obj_mod.write(writer, points, material_index, properties, f)
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
          obj_mod.write(writer, boundaries, material_index, properties, f)
  # write materials
  if len(materials) > 0:
    writer.write("\n".join(materials) + "\n")

def dummyProgress(progress):
  pass
