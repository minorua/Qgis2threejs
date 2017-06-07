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
import struct
from qgis.core import QgsProject, QgsRectangle

from . import gdal2threejs
from .exportlayer import LayerExporter
from .propertyreader import DEMPropertyReader
from .qgis2threejscore import GDALDEMProvider
from . import qgis2threejstools as tools
from .qgis2threejstools import logMessage


class DEMLayerExporter(LayerExporter):

  def __init__(self, settings, imageManager, progress=None):
    LayerExporter.__init__(self, settings, imageManager, progress)

  def export(self, layerId, properties, jsLayerId, visible=True, pathRoot=None, urlRoot=None):
    #if self.settings.exportMode == ExportSettings.PLAIN_SIMPLE:
      #writeSimpleDEM(writer, demProperties, progress)
    #else:
      #writeMultiResDEM(writer, demProperties, progress)

    prop = DEMPropertyReader(properties)

    # DEM provider
    provider = self.settings.demProviderByLayerId(layerId)
    #TODO: if provider is None: return None
    if isinstance(provider, GDALDEMProvider):
      layer = QgsProject.instance().mapLayer(layerId)
      layerName = layer.name()
    else:
      layer = None
      layerName = provider.name()

    # grid
    grid_size = prop.demSize(self.settings.mapSettings.outputSize())
    grid_values = provider.read(grid_size.width(), grid_size.height(), self.settings.baseExtent)

    # DEM block
    mapTo3d = self.settings.mapTo3d()
    block = DEMBlock(grid_size.width(), grid_size.height(), grid_values, mapTo3d.planeWidth, mapTo3d.planeHeight, 0, 0)
    block.zShift(mapTo3d.verticalShift)
    block.zScale(mapTo3d.multiplierZ)

    # write grid values to an external binary file (file export mode)
    if pathRoot is not None:
      block.write(pathRoot + "_DEM0.bin")

    #TODO: move to DEMBlock?
    # material option
    texture_scale = properties.get("comboBox_TextureSize", 100) // 100
    transparency = properties.get("spinBox_demtransp", 0)
    transp_background = properties.get("checkBox_TransparentBackground", False)

    # display type
    canvas_size = self.settings.mapSettings.outputSize()
    if properties.get("radioButton_MapCanvas", False):
      if texture_scale == 1:
        mi = self.materialManager.getCanvasImageIndex(transparency, transp_background)
      else:
        mi = self.materialManager.getMapImageIndex(canvas_size.width() * texture_scale, canvas_size.height() * texture_scale, self.settings.baseExtent, transparency, transp_background)

    elif properties.get("radioButton_LayerImage", False):
      layerids = properties.get("layerImageIds", [])
      mi = self.materialManager.getLayerImageIndex(layerids, canvas_size.width() * texture_scale, canvas_size.height() * texture_scale, self.settings.baseExtent, transparency, transp_background)

    elif properties.get("radioButton_ImageFile", False):
      filepath = properties.get("lineEdit_ImageFile", "")
      mi = self.materialManager.getImageFileIndex(filepath, transparency, transp_background, True)

    else:   #.get("radioButton_SolidColor", False)
      mi = self.materialManager.getMeshLambertIndex(properties.get("lineEdit_Color", ""), transparency, True)

    #elif properties.get("radioButton_Wireframe", False):
    #  mi = self.materialManager.getWireframeIndex(properties["lineEdit_Color"], transparency)

    p = {
      "type": "dem",
      "name": layerName,
      "queryable": 1,
      "shading": properties.get("checkBox_Shading", True),
      "visible": visible
      }

    url = None if urlRoot is None else urlRoot + "_DEM0.bin"
    b = block.export(url)
    b["mat"] = mi

    return {
      "type": "layer",
      "id": jsLayerId,
      "properties": p,
      "data": {
        "blocks": [b],
        "materials": self.materialManager.export(self.imageManager, pathRoot, urlRoot)
        },
      "PROPERTIES": properties    # debug
      }


class DEMBlock:

  def __init__(self, grid_width, grid_height, grid_values, plane_width, plane_height, offsetX, offsetY):
    self.grid_width = grid_width
    self.grid_height = grid_height
    self.grid_values = grid_values
    self.plane_width = plane_width
    self.plane_height = plane_height
    self.offsetX = offsetX
    self.offsetY = offsetY

    self.orig_stats = {"max": max(grid_values), "min": min(grid_values)}
    self.rect = QgsRectangle(offsetX - plane_width * 0.5, offsetY - plane_height * 0.5,
                             offsetX + plane_width * 0.5, offsetY + plane_height * 0.5)
    self.clip_geometry = None

  def setClipGeometry(self, geometry):
    self.clip_geometry = geometry

  def zShift(self, shift):
    if shift != 0:
      self.grid_values = [x + shift for x in self.grid_values]

  def zScale(self, scale):
    if scale != 1:
      self.grid_values = [x * scale for x in self.grid_values]

  def export(self, extFileUrl=None):
    """extFileUrl: should be specified when the grid values are written to an extenal binary file."""
    g = {"width": self.grid_width,
         "height": self.grid_height}
         #"csv": ",".join(map(gdal2threejs.formatValue, self.grid_values))}

    if extFileUrl is None:
      g["array"] = self.grid_values
    else:
      g["url"] = extFileUrl

    return {"grid": g,
            "width": self.plane_width,
            "height": self.plane_height,
            "translate": [self.offsetX, self.offsetY, 0]}

  def write(self, filepath):
    """write grid values to an external binary file"""
    with open(filepath, "wb") as f:
      f.write(struct.pack("{}f".format(self.grid_width * self.grid_height), *self.grid_values))

  def _write(self, writer):
    mapTo3d = writer.settings.mapTo3d()

    writer.write("bl = lyr.addBlock({0}, {1});\n".format(pyobj2js(self.properties), pyobj2js(bool(self.clip_geometry))))
    writer.write("bl.data = [{0}];\n".format(",".join(map(gdal2threejs.formatValue, self.grid_values))))

    # clipped with polygon layer
    if self.clip_geometry:
      z_func = lambda x, y: 0
      transform_func = lambda x, y, z: mapTo3d.transform(x, y, z)

      geom = PolygonGeometry.fromQgsGeometry(self.clip_geometry, z_func, transform_func)
      geom.splitPolygon(writer.triangleMesh(self.grid_width, self.grid_height))

      polygons = []
      for polygon in geom.polygons:
        bnds = []
        for boundary in polygon:
          bnds.append([[pt.x, pt.y] for pt in boundary])
        polygons.append(bnds)

      writer.write("bl.clip = {};\n")
      writer.write("bl.clip.polygons = {0};\n".format(pyobj2js(polygons)))

      triangles = Triangles()
      polygons = []
      for polygon in geom.split_polygons:
        boundary = polygon[0]
        if len(polygon) == 1 and len(boundary) == 4:
          triangles.addTriangle(boundary[0], boundary[2], boundary[1])    # vertex order should be counter-clockwise
        else:
          bnds = [[[pt.x, pt.y] for pt in bnd] for bnd in polygon]
          polygons.append(bnds)

      vf = {"v": [[pt.x, pt.y] for pt in triangles.vertices], "f": triangles.faces}
      writer.write("bl.clip.triangles = {0};\n".format(pyobj2js(vf)))
      writer.write("bl.clip.split_polygons = {0};\n".format(pyobj2js(polygons)))

  def getValue(self, x, y):

    def _getValue(gx, gy):
      return self.grid_values[gx + self.grid_width * gy]

    if 0 <= x and x <= self.grid_width - 1 and 0 <= y and y <= self.grid_height - 1:
      ix, iy = int(x), int(y)
      sx, sy = x - ix, y - iy

      z11 = _getValue(ix, iy)
      z21 = 0 if x == self.grid_width - 1 else _getValue(ix + 1, iy)
      z12 = 0 if y == self.grid_height - 1 else _getValue(ix, iy + 1)
      z22 = 0 if x == self.grid_width - 1 or y == self.grid_height - 1 else _getValue(ix + 1, iy + 1)

      return (1 - sx) * ((1 - sy) * z11 + sy * z12) + sx * ((1 - sy) * z21 + sy * z22)    # bilinear interpolation

    return 0    # as safe null value

  def gridPointToPoint(self, x, y):
    x = self.rect.xMinimum() + self.rect.width() / (self.grid_width - 1) * x
    y = self.rect.yMaximum() - self.rect.height() / (self.grid_height - 1) * y
    return x, y

  def pointToGridPoint(self, x, y):
    x = (x - self.rect.xMinimum()) / self.rect.width() * (self.grid_width - 1)
    y = (self.rect.yMaximum() - y) / self.rect.height() * (self.grid_height - 1)
    return x, y


class DEMBlocks:

  def __init__(self):
    self.blocks = []

  def appendBlock(self, block):
    self.blocks.append(block)

  def appendBlocks(self, blocks):
    self.blocks += blocks

  def processEdges(self):
    """for now, this function is designed for simple resampling mode with surroundings"""
    count = len(self.blocks)
    if count < 9:
      return

    ci = (count - 1) // 2
    size = int(count ** 0.5)

    center = self.blocks[0]
    blocks = self.blocks[1:ci + 1] + [center] + self.blocks[ci + 1:]

    grid_width, grid_height, grid_values = center.grid_width, center.grid_height, center.grid_values
    for istop, neighbor in enumerate([blocks[ci - size], blocks[ci + size]]):
      if grid_width == neighbor.grid_width:
        continue

      y = grid_height - 1 if not istop else 0
      for x in range(grid_width):
        gx, gy = center.gridPointToPoint(x, y)
        gx, gy = neighbor.pointToGridPoint(gx, gy)
        grid_values[x + grid_width * y] = neighbor.getValue(gx, gy)

    for isright, neighbor in enumerate([blocks[ci - 1], blocks[ci + 1]]):
      if grid_height == neighbor.grid_height:
        continue

      x = grid_width - 1 if isright else 0
      for y in range(grid_height):
        gx, gy = center.gridPointToPoint(x, y)
        gx, gy = neighbor.pointToGridPoint(gx, gy)
        grid_values[x + grid_width * y] = neighbor.getValue(gx, gy)

  def stats(self):
    if len(self.blocks) == 0:
      return {"max": 0, "min": 0}

    block = self.blocks[0]
    stats = {"max": block.orig_stats["max"], "min": block.orig_stats["min"]}
    for block in self.blocks[1:]:
      stats["max"] = max(block.orig_stats["max"], stats["max"])
      stats["min"] = min(block.orig_stats["min"], stats["min"])
    return stats

  def write(self, writer, separated=False):
    for block in self.blocks:
      if separated:
        writer.nextFile(True)

      block.write(writer)


def dummyProgress(progress=None, statusMsg=None):
  pass
