# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
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
from qgis.core import QgsPoint, QgsRectangle


class QuadNode:

  def __init__(self, parent, rect, location, height=0):
    self.parent = parent
    self.rect = rect
    self.location = location
    self.height = height
    self.subNodes = []

  def subdivideRecursively(self, rect, maxHeight):
    if maxHeight <= self.height:
      return
    self.subNodes = []
    for y in range(2):
      for x in range(2):
        xmin = self.rect.xMinimum() + 0.5 * x * self.rect.width()
        ymin = self.rect.yMinimum() + 0.5 * (1 - y) * self.rect.height()
        xmax = xmin + 0.5 * self.rect.width()
        ymax = ymin + 0.5 * self.rect.height()
        quadrect = QgsRectangle(xmin, ymin, xmax, ymax)
        node = self.__class__(self, quadrect, 2 * y + x, self.height + 1)
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
    if not self.rect.contains(point):
      return None
    if len(self.subNodes) == 0:
      return self
    x = min(1, int(2 * (point.x() - self.rect.xMinimum()) / self.rect.width()))
    y = min(1, int(2 * (self.rect.yMaximum() - point.y()) / self.rect.height()))
    return self.subNodes[2 * y + x].quadByPosition(point)


class QuadTree:

  NodeClass = QuadNode

  UP = 0
  LEFT = 1
  RIGHT = 2
  DOWN = 3

  def __init__(self, rect=None):
    if rect is None:
      rect = QgsRectangle(0, 0, 1, 1)
    self.rect = rect
    self.root = self.NodeClass(self, rect, 0)
    self.focusRect = None
    self.height = 0

  def buildTreeByRect(self, rect, height):
    if not self.rect.intersects(rect):
      return False
    self.focusRect = QgsRectangle(rect)
    self.height = height
    self.root.subdivideRecursively(self.focusRect, height)
    return True

  def buildTreeByPoint(self, point, height):
    return self.buildTreeByRect(QgsRectangle(point.x(), point.y(), point.x(), point.y()), height)

  def quads(self, sorted=False):
    q = self.root.listTopQuads([])
    if sorted:
      q.sort(key=lambda x: x.height)    # sort by height
    return q

  def quadByPosition(self, point):
    if point and self.rect.contains(point):
      return self.root.quadByPosition(point)
    return None

  def neighbors(self, quad):
    # if neighbor count of one direction is not only one, returns one of neighbors. so totally returns 4 neighbors.
    quads = [None] * 4
    if len(quad.parent.subNodes) == 0:
      return quads
    rect = quad.rect
    center = rect.center()
    m = 0.5 ** self.height
    quads[self.UP] = self.quadByPosition(QgsPoint(center.x(), rect.yMaximum() + m * rect.height()))
    quads[self.LEFT] = self.quadByPosition(QgsPoint(rect.xMinimum() - m * rect.width(), center.y()))
    quads[self.RIGHT] = self.quadByPosition(QgsPoint(rect.xMaximum() + m * rect.width(), center.y()))
    quads[self.DOWN] = self.quadByPosition(QgsPoint(center.x(), rect.yMinimum() - m * rect.height()))
    return quads


class QuadList:

  def __init__(self):
    self.quads = []
    self.calculatedRect = None
    self.sorted = False

  def addQuad(self, quad):
    self.quads.append(quad)
    self.calculatedRect = None
    self.sorted = False

  def count(self):
    return len(self.quads)

  def rect(self):
    if self.calculatedRect:
      return self.calculatedRect
    if len(self.quads) == 0:
      return QgsRectangle()
    rect = QgsRectangle(self.quads[0].rect)
    for quad in self.quads[1:]:
      rect.unionRect(quad.rect)
    self.calculatedRect = rect
    return rect

  def width(self):
    if len(self.quads) == 0:
      return 0
    return int(self.rect().width() / self.quads[0].rect.width() + 0.1)

  def height(self):
    if len(self.quads) == 0:
      return 0
    return int(self.rect().height() / self.quads[0].rect.height() + 0.1)

  def sort(self):
    if self.sorted:
      return
    rect = self.rect()
    sorted_quads = [None] * self.width() * self.height()
    for quad in self.quads:
      x = int((quad.rect.xMinimum() - rect.xMinimum()) / quad.rect.width() + 0.1)
      y = int((rect.yMaximum() - quad.rect.yMaximum()) / quad.rect.height() + 0.1)
      sorted_quads[x + y * self.width()] = quad
    self.quads = sorted_quads
    self.sorted = True


class DEMQuadNode(QuadNode):

  def __init__(self, parent, rect, location, height=0):
    QuadNode.__init__(self, parent, rect, location, height)

  def setData(self, width, height, values):
    self.dem_width = width
    self.dem_height = height
    self.dem_values = values

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


class DEMQuadTree(QuadTree):

  NodeClass = DEMQuadNode

  def processEdges(self):
    """ fit edges of every block with next block of different resolution"""

    for quad in self.quads(sorted=True):
      if quad == 1:
        continue

      dem_width, dem_height, dem_values = quad.dem_width, quad.dem_height, quad.dem_values
      for direction, neighbor in enumerate(self.neighbors(quad)):
        if neighbor is None or quad.height <= neighbor.height:
          continue

        if direction in [DEMQuadTree.UP, DEMQuadTree.DOWN]:
          y = 0 if direction == DEMQuadTree.UP else dem_height - 1
          for x in range(dem_width):
            gx, gy = quad.gridPointToPoint(x, y)
            gx, gy = neighbor.pointToGridPoint(gx, gy)
            dem_values[x + dem_width * y] = neighbor.getValue(gx, gy)

        else:   # LEFT or RIGHT
          x = 0 if direction == DEMQuadTree.LEFT else dem_width - 1
          for y in range(dem_height):
            gx, gy = quad.gridPointToPoint(x, y)
            gx, gy = neighbor.pointToGridPoint(gx, gy)
            dem_values[x + dem_width * y] = neighbor.getValue(gx, gy)


class DEMQuadList(QuadList):

  def __init__(self, dem_width, dem_height):
    QuadList.__init__(self)
    self.dem_width = dem_width
    self.dem_height = dem_height

  def addQuad(self, quad):   # quad: DEMQuadNode
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
          dem_values += self.quads[col + row * width].dem_values[i:i + self.dem_width - x0]
    return dem_values
