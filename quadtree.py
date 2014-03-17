# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
                              -------------------
        begin                : 2013-12-29
        copyright            : (C) 2013 Minoru Akagi
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
from qgis.core import *

class QuadNode:
  def __init__(self, parent, extent, location, height=0):
    self.parent = parent
    self.extent = extent
    self.location = location
    self.height = height
    self.subNodes = []
    self.data = None

  def subdivideRecursively(self, rect, maxHeight):
    if maxHeight <= self.height:
      return
    self.subNodes = []
    for y in range(2):
      for x in range(2):
        xmin = self.extent.xMinimum() + 0.5 * x * self.extent.width()
        ymin = self.extent.yMinimum() + 0.5 * (1 - y) * self.extent.height()
        xmax = xmin + 0.5 * self.extent.width()
        ymax = ymin + 0.5 * self.extent.height()
        quadrect = QgsRectangle(xmin, ymin, xmax, ymax)
        node = QuadNode(self, quadrect, 2 * y + x, self.height + 1)
        self.subNodes.append(node)
        if quadrect.intersects(rect):
          node.subdivideRecursively(rect, maxHeight)

  def listTopQuads(self, quadlist):
    if len(self.subNodes):
      for node in self.subNodes:
        node.listTopQuads(quadlist)
    else:
      quadlist.append(self)
    return quadlist

  def quadByPosition(self, point):
    if not self.extent.contains(point):
      return None
    if len(self.subNodes) == 0:
      return self
    x = min(1, int(2 * (point.x() - self.extent.xMinimum()) / self.extent.width()))
    y = min(1, int(2 * (self.extent.yMaximum() - point.y()) / self.extent.height()))
    return self.subNodes[2 * y + x].quadByPosition(point)

class QuadTree:
  UP = 0
  LEFT = 1
  RIGHT = 2
  DOWN = 3

  def __init__(self, extent=None):
    self.extent = extent
    self.root = QuadNode(self, self.extent, 0)
    self.focusRect = None

  def setExtent(self, extent):
    self.extent = extent

  def buildTreeByRect(self, rect, height):
    if not self.extent.intersects(rect):
      return
    self.focusRect = QgsRectangle(rect)
    self.height = height
    self.root.subdivideRecursively(self.focusRect, height)

  def buildTreeByPoint(self, point, height):
    self.buildTreeByRect(QgsRectangle(point.x(), point.y(), point.x(), point.y()), height)

  def quads(self):
    return self.root.listTopQuads([])

  def quadByPosition(self, point):
    if not point or not self.extent.contains(point):
      return None
    return self.root.quadByPosition(point)

  def neighbors(self, quad):
    # if neighbor count of one direction is not only one, returns one of neighbors. so totally returns 4 neighbors.
    quads = [None] * 4
    if len(quad.parent.subNodes) == 0:
      return quads
    extent = quad.extent
    center = extent.center()
    m = 0.5 ** self.height
    quads[self.UP] = self.quadByPosition(QgsPoint(center.x(), extent.yMaximum() + m * extent.height()))
    quads[self.LEFT] = self.quadByPosition(QgsPoint(extent.xMinimum() - m * extent.width(), center.y()))
    quads[self.RIGHT] = self.quadByPosition(QgsPoint(extent.xMaximum() + m * extent.width(), center.y()))
    quads[self.DOWN] = self.quadByPosition(QgsPoint(center.x(), extent.yMinimum() - m * extent.height()))
    return quads

class QuadList:
  def __init__(self):
    self.quads = []
    self.calculatedExtent = None
    self.sorted = False

  def addQuad(self, quad):
    self.quads.append(quad)
    self.calculatedExtent = None
    self.sorted = False

  def count(self):
    return len(self.quads)

  def extent(self):
    if self.calculatedExtent is not None:
      return self.calculatedExtent
    if len(self.quads) == 0:
      return QgsRectangle()
    extent = QgsRectangle(self.quads[0].extent)
    for quad in self.quads[1:]:
      extent.unionRect(quad.extent)
    self.calculatedExtent = extent
    return extent

  def width(self):
    if len(self.quads) == 0:
      return 0
    return int(self.extent().width() / self.quads[0].extent.width() + 0.1)

  def height(self):
    if len(self.quads) == 0:
      return 0
    return int(self.extent().height() / self.quads[0].extent.height() + 0.1)

  def sort(self):
    if self.sorted:
      return
    extent = self.extent()
    sorted_quads = [None] * self.width() * self.height()
    for quad in self.quads:
      x = int((quad.extent.xMinimum() - extent.xMinimum()) / quad.extent.width() + 0.1)
      y = int((extent.yMaximum() - quad.extent.yMaximum()) / quad.extent.height() + 0.1)
      sorted_quads[x + y * self.width()] = quad
    self.quads = sorted_quads
    self.sorted = True

class DEMQuadList(QuadList):
  def __init__(self, dem_width, dem_height):
    QuadList.__init__(self)
    self.dem_width = dem_width
    self.dem_height = dem_height

  def addQuad(self, quad, dem):
    quad.data = dem
    QuadList.addQuad(self, quad)

  def unitedDEM(self):
    self.sort()
    width = self.width()
    height = self.height()
    dem_values = []
    for row in range(height):
      y0 = 0 if row == 0 else 1
      for y in range(y0, self.dem_height):
        for col in range(width):
          x0 = 0 if col == 0 else 1
          i = y * self.dem_width + x0
          dem_values += self.quads[col + row * width].data[i:i + self.dem_width - x0]
    return dem_values
