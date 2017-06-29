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
from .datamanager import MaterialManager
from .exportlayer import LayerExporter
from .propertyreader import DEMPropertyReader
from .qgis2threejscore import GDALDEMProvider
from . import qgis2threejstools as tools
from .qgis2threejstools import logMessage


class DEMLayerExporter(LayerExporter):

  def __init__(self, settings, imageManager, layerId, properties, jsLayerId, visible=True, pathRoot=None, urlRoot=None, progress=None):
    """if both pathRoot and urlRoot are None, object is built in all_in_dict mode."""
    LayerExporter.__init__(self, settings, imageManager, layerId, properties, jsLayerId, visible, progress)
    self.pathRoot = pathRoot
    self.urlRoot = urlRoot

  def build(self, export_blocks=True):
    #if self.settings.exportMode == ExportSettings.PLAIN_SIMPLE:
      #writeSimpleDEM(writer, demProperties, progress)
    #else:
      #writeMultiResDEM(writer, demProperties, progress)

    prop = DEMPropertyReader(self.properties)

    # DEM provider
    provider = self.settings.demProviderByLayerId(self.layerId)
    if isinstance(provider, GDALDEMProvider):
      layer = QgsProject.instance().mapLayer(self.layerId)
      layerName = layer.name()
    elif provider:
      layer = None
      layerName = provider.name()
    else:
      return None

    p = {
      "type": "dem",
      "name": layerName,
      "queryable": 1,
      "shading": self.properties.get("checkBox_Shading", True),
      "visible": self.visible
      }

    d = {
      "type": "layer",
      "id": self.jsLayerId,
      "properties": p,
      "PROPERTIES": self.properties    # debug
      }

    # DEM block
    if export_blocks:
      grid_size = prop.demSize(self.settings.mapSettings.outputSize())

      blockIndex = 0
      mapTo3d = self.settings.mapTo3d()
      block = DEMBlockExporter(self.settings,
                               self.imageManager,
                               self.layerId,
                               self.properties,
                               self.jsLayerId,
                               blockIndex,
                               provider,
                               grid_size,
                               self.settings.baseExtent,
                               mapTo3d.planeWidth,
                               mapTo3d.planeHeight,
                               offsetX=0,
                               offsetY=0,
                               clip_geometry=None,
                               pathRoot=self.pathRoot,
                               urlRoot=self.urlRoot)
      b = block.build()
      d["data"] = [b]

    return d


class DEMBlockExporter:

  def __init__(self, settings, imageManager, layerId, properties, jsLayerId, blockIndex, provider, grid_size, extent, planeWidth, planeHeight, offsetX=0, offsetY=0, clip_geometry=None, pathRoot=None, urlRoot=None):
    self.settings = settings
    self.imageManager = imageManager
    self.materialManager = MaterialManager()

    self.layerId = layerId
    self.properties = properties
    self.jsLayerId = jsLayerId
    self.blockIndex = blockIndex
    self.provider = provider
    self.grid_size = grid_size
    self.extent = extent
    self.planeWidth = planeWidth
    self.planeHeight = planeHeight
    self.offsetX = offsetX
    self.offsetY = offsetY
    self.clip_geometry = clip_geometry
    self.pathRoot = pathRoot
    self.urlRoot = urlRoot

    #self.orig_stats = {"max": max(grid_values), "min": min(grid_values)}
    #self.rect = QgsRectangle(offsetX - plane_width * 0.5, offsetY - plane_height * 0.5,
    #                         offsetX + plane_width * 0.5, offsetY + plane_height * 0.5)

  def build(self):
    mapTo3d = self.settings.mapTo3d()
    shift = mapTo3d.verticalShift
    scale = mapTo3d.multiplierZ

    grid_values = self.provider.read(self.grid_size.width(), self.grid_size.height(), self.extent)
    if shift != 0:
      grid_values = [x + shift for x in grid_values]

    if scale != 1:
      grid_values = [x * scale for x in grid_values]

    # write grid values to an external binary file
    if self.pathRoot is not None:
      with open(self.pathRoot + "_DEM{0}.bin".format(self.blockIndex), "wb") as f:
        f.write(struct.pack("{0}f".format(self.grid_size.width() * self.grid_size.height()), *grid_values))

    # block data
    g = {"width": self.grid_size.width(),
         "height": self.grid_size.height()}

    extFileUrl = None if self.urlRoot is None else self.urlRoot + "_DEM{0}.bin".format(self.blockIndex)
    if extFileUrl is None:
      g["array"] = grid_values
    else:
      g["url"] = extFileUrl

    # material
    material = self.material()

    b = {"type": "block",
         "layer": self.layerId,
         "block": self.blockIndex,
         "grid": g,
         "width": self.planeWidth,
         "height": self.planeHeight,
         "translate": [self.offsetX, self.offsetY, 0],
         "material": material}

    # clipped with polygon layer
    if self.clip_geometry:
      b["clip"] = self.clipped()

    # sides and bottom
    if self.properties.get("checkBox_Sides", False):
      b["sides"] = True

    # frame
    if self.properties.get("checkBox_Frame", False) and not self.properties.get("checkBox_Clip", False):
      b["frame"] = True 

    return b

  def material(self):
    # material options
    properties = self.properties
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

    materials = self.materialManager.build(self.imageManager, self.pathRoot, self.urlRoot)
    return materials[mi]

  #TODO
  def clipped(self):
    mapTo3d = self.settings.mapTo3d()
    z_func = lambda x, y: 0
    transform_func = lambda x, y, z: mapTo3d.transform(x, y, z)

    geom = PolygonGeometry.fromQgsGeometry(self.clip_geometry, z_func, transform_func)
    geom.splitPolygon(writer.triangleMesh(self.grid_width, self.grid_height))

    #TODO: geom.toList()
    polygons = []
    for polygon in geom.polygons:
      bnds = []
      for boundary in polygon:
        bnds.append([[pt.x, pt.y] for pt in boundary])
      polygons.append(bnds)

    triangles = Triangles()
    split_polygons = []
    for polygon in geom.split_polygons:
      boundary = polygon[0]
      if len(polygon) == 1 and len(boundary) == 4:
        triangles.addTriangle(boundary[0], boundary[2], boundary[1])    # vertex order should be counter-clockwise
      else:
        bnds = [[[pt.x, pt.y] for pt in bnd] for bnd in polygon]
        split_polygons.append(bnds)

    return {"polygons": polygons,
            "triangles": {"v": [[pt.x, pt.y] for pt in triangles.vertices],
                          "f": triangles.faces},
            "split_polygons": split_polygons}

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
