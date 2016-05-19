# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DEMBlock
                              -------------------
        begin                : 2015-05-23
        copyright            : (C) 2015 Minoru Akagi
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
from qgis.core import QgsRectangle

from . import gdal2threejs
from .geometry import PolygonGeometry, Triangles
from .qgis2threejstools import pyobj2js


class DEMBlock:

  def __init__(self, dem_width, dem_height, dem_values, plane_width, plane_height, offsetX, offsetY):
    self.dem_width = dem_width
    self.dem_height = dem_height
    self.dem_values = dem_values
    self.plane_width = plane_width
    self.plane_height = plane_height
    self.offsetX = offsetX
    self.offsetY = offsetY

    self.orig_stats = {"max": max(dem_values), "min": min(dem_values)}
    self.rect = QgsRectangle(offsetX - plane_width * 0.5, offsetY - plane_height * 0.5,
                             offsetX + plane_width * 0.5, offsetY + plane_height * 0.5)

    self.properties = {"width": dem_width, "height": dem_height}
    self.properties["plane"] = {"width": plane_width, "height": plane_height,
                                "offsetX": offsetX, "offsetY": offsetY}

    self.clip_geometry = None

  def set(self, key, value):
    """set property"""
    self.properties[key] = value

  def setClipGeometry(self, geometry):
    self.clip_geometry = geometry

  def zShift(self, shift):
    if shift != 0:
      self.dem_values = [x + shift for x in self.dem_values]

  def zScale(self, scale):
    if scale != 1:
      self.dem_values = [x * scale for x in self.dem_values]

  def write(self, writer):
    mapTo3d = writer.settings.mapTo3d()

    writer.write("bl = lyr.addBlock({0}, {1});\n".format(pyobj2js(self.properties), pyobj2js(bool(self.clip_geometry))))
    writer.write("bl.data = [{0}];\n".format(",".join(map(gdal2threejs.formatValue, self.dem_values))))

    # clipped with polygon layer
    if self.clip_geometry:
      z_func = lambda x, y: 0
      transform_func = lambda x, y, z: mapTo3d.transform(x, y, z)

      geom = PolygonGeometry.fromQgsGeometry(self.clip_geometry, z_func, transform_func)
      geom.splitPolygon(writer.triangleMesh(self.dem_width, self.dem_height))

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
      return self.dem_values[gx + self.dem_width * gy]

    if 0 <= x and x <= self.dem_width - 1 and 0 <= y and y <= self.dem_height - 1:
      ix, iy = int(x), int(y)
      sx, sy = x - ix, y - iy

      z11 = _getValue(ix, iy)
      z21 = 0 if x == self.dem_width - 1 else _getValue(ix + 1, iy)
      z12 = 0 if y == self.dem_height - 1 else _getValue(ix, iy + 1)
      z22 = 0 if x == self.dem_width - 1 or y == self.dem_height - 1 else _getValue(ix + 1, iy + 1)

      return (1 - sx) * ((1 - sy) * z11 + sy * z12) + sx * ((1 - sy) * z21 + sy * z22)    # bilinear interpolation

    return 0    # as safe null value

  def gridPointToPoint(self, x, y):
    x = self.rect.xMinimum() + self.rect.width() / (self.dem_width - 1) * x
    y = self.rect.yMaximum() - self.rect.height() / (self.dem_height - 1) * y
    return x, y

  def pointToGridPoint(self, x, y):
    x = (x - self.rect.xMinimum()) / self.rect.width() * (self.dem_width - 1)
    y = (self.rect.yMaximum() - y) / self.rect.height() * (self.dem_height - 1)
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

    ci = (count - 1) / 2
    size = int(count ** 0.5)

    center = self.blocks[0]
    blocks = self.blocks[1:ci + 1] + [center] + self.blocks[ci + 1:]

    dem_width, dem_height, dem_values = center.dem_width, center.dem_height, center.dem_values
    for istop, neighbor in enumerate([blocks[ci - size], blocks[ci + size]]):
      if dem_width == neighbor.dem_width:
        continue

      y = dem_height - 1 if not istop else 0
      for x in range(dem_width):
        gx, gy = center.gridPointToPoint(x, y)
        gx, gy = neighbor.pointToGridPoint(gx, gy)
        dem_values[x + dem_width * y] = neighbor.getValue(gx, gy)

    for isright, neighbor in enumerate([blocks[ci - 1], blocks[ci + 1]]):
      if dem_height == neighbor.dem_height:
        continue

      x = dem_width - 1 if isright else 0
      for y in range(dem_height):
        gx, gy = center.gridPointToPoint(x, y)
        gx, gy = neighbor.pointToGridPoint(gx, gy)
        dem_values[x + dem_width * y] = neighbor.getValue(gx, gy)

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
