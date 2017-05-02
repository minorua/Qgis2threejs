# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RotatedRect
                              -------------------
        begin                : 2015-03-05
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
import math
from qgis.core import Qgis, QgsPoint, QgsRectangle, QgsGeometry


class RotatedRect:

  def __init__(self, center, width, height, rotation=0):
    """
    args:
      center        -- QgsPoint
      width, height -- float
      rotation      -- int/float
    """
    self._center = center
    self._width = width
    self._height = height
    self._rotation = rotation
    self._updateDerived()

  def clone(self):
    return RotatedRect(self._center, self._width, self._height, self._rotation)

  def _updateDerived(self):
    self._unrotated_rect = self._unrotatedRect()

  def _unrotatedRect(self):
    center = self._center
    half_width = self._width / 2
    half_height = self._height / 2
    return QgsRectangle(center.x() - half_width, center.y() - half_height,
                        center.x() + half_width, center.y() + half_height)

  @staticmethod
  def rotatePoint(point, degrees, origin=None):
    """Rotate point around the origin"""
    theta = degrees * math.pi / 180
    c = math.cos(theta)
    s = math.sin(theta)
    x = point.x()
    y = point.y()

    if origin:
      x -= origin.x()
      y -= origin.y()

    # rotate counter-clockwise
    xd = x * c - y * s
    yd = x * s + y * c

    if origin:
      xd += origin.x()
      yd += origin.y()
    return QgsPoint(xd, yd)

  def normalizePoint(self, x, y):
    """Normalize given point. In result, lower-left is (0, 0) and upper-right is (1, 1)."""
    pt = QgsPoint(x, y)
    if self._rotation:
      pt = self.rotatePoint(pt, -self._rotation, self._center)
    rect = self._unrotated_rect
    return QgsPoint((pt.x() - rect.xMinimum()) / rect.width(),
                    (pt.y() - rect.yMinimum()) / rect.height())

  def scale(self, s):
    self._width *= s
    self._height *= s
    self._updateDerived()
    return self

  def rotate(self, degrees, origin=None):
    """Rotate the center of extent around the origin
    args:
      degrees -- int/float (counter-clockwise)
      origin  -- QgsPoint
    """
    self._rotation += degrees
    if origin is None:
      return self
    self._center = self.rotatePoint(self._center, degrees, origin)
    self._updateDerived()
    return self

  def point(self, norm_point, y_inverted=False):
    """
    args:
      norm_point -- QgsPoint (0 <= x <= 1, 0 <= y <= 1)
      y_inverted -- If True, lower-left is (0, 1) and upper-right is (1, 0).
                    Or else lower-left is (0, 0) and upper-right is (1, 1).
    """
    ur_rect = self._unrotated_rect
    x = ur_rect.xMinimum() + norm_point.x() * ur_rect.width()
    if y_inverted:
      y = ur_rect.yMaximum() - norm_point.y() * ur_rect.height()
    else:
      y = ur_rect.yMinimum() + norm_point.y() * ur_rect.height()
    return self.rotatePoint(QgsPoint(x, y), self._rotation, self._center)

  def subrectangle(self, norm_rect, y_inverted=False):
    """
    args:
      norm_rect  -- QgsRectangle (0 <= xmin, 0 <= ymin, xmax <= 1, ymax <= 1)
      y_inverted -- If True, lower-left is (0, 1) and upper-right is (1, 0).
                    Or else lower-left is (0, 0) and upper-right is (1, 1).
    """
    ur_rect = self._unrotated_rect
    xmin = ur_rect.xMinimum() + norm_rect.xMinimum() * ur_rect.width()
    xmax = ur_rect.xMinimum() + norm_rect.xMaximum() * ur_rect.width()
    if y_inverted:
      ymin = ur_rect.yMaximum() - norm_rect.yMaximum() * ur_rect.height()
      ymax = ur_rect.yMaximum() - norm_rect.yMinimum() * ur_rect.height()
    else:
      ymin = ur_rect.yMinimum() + norm_rect.yMinimum() * ur_rect.height()
      ymax = ur_rect.yMinimum() + norm_rect.yMaximum() * ur_rect.height()

    rect = QgsRectangle(xmin, ymin, xmax, ymax)
    return RotatedRect(rect.center(), rect.width(), rect.height()).rotate(self._rotation, self._center)

  @classmethod
  def fromMapSettings(cls, mapSettings):
    extent = mapSettings.visibleExtent() if Qgis.QGIS_VERSION_INT >= 20300 else mapSettings.extent()
    rotation = mapSettings.rotation() if Qgis.QGIS_VERSION_INT >= 20700 else 0
    if rotation == 0:
      return cls(extent.center(), extent.width(), extent.height())

    mupp = mapSettings.mapUnitsPerPixel()
    canvas_size = mapSettings.outputSize()
    return cls(extent.center(), mupp * canvas_size.width(), mupp * canvas_size.height(), rotation)

  def toMapSettings(self, mapSettings=None):
    if mapSettings is None:
      if Qgis.QGIS_VERSION_INT >= 20300:
        from qgis.core import QgsMapSettings
        mapSettings = QgsMapSettings()
      else:
        return None
    mapSettings.setExtent(self._unrotated_rect)
    mapSettings.setRotation(self._rotation)
    return mapSettings

  def boundingBox(self):
    theta = self._rotation * math.pi / 180
    c = abs(math.cos(theta))
    s = abs(math.sin(theta))
    hw = (self._width * c + self._height * s) / 2
    hh = (self._width * s + self._height * c) / 2
    return QgsRectangle(self._center.x() - hw, self._center.y() - hh,
                        self._center.x() + hw, self._center.y() + hh)

  def geotransform(self, cols, rows, is_grid_point=True):
    center = self._center
    ur_rect = self._unrotated_rect
    rotation = self._rotation

    segments_x = cols
    segments_y = rows
    if is_grid_point:
      segments_x -= 1
      segments_y -= 1

    if rotation:
      # rotate top-left corner of unrotated extent around center of extent counter-clockwise (map rotates clockwise)
      rpt = self.rotatePoint(QgsPoint(ur_rect.xMinimum(), ur_rect.yMaximum()), rotation, center)
      res_lr = self._width / segments_x
      res_ul = self._height / segments_y

      theta = rotation * math.pi / 180
      c = math.cos(theta)
      s = math.sin(theta)
      geotransform = [rpt.x(), res_lr * c, res_ul * s, rpt.y(), res_lr * s, -res_ul * c]
      if is_grid_point:
        # top-left corner of extent corresponds to center of top-left pixel.
        geotransform[0] -= 0.5 * geotransform[1] + 0.5 * geotransform[2]
        geotransform[3] -= 0.5 * geotransform[4] + 0.5 * geotransform[5]
    else:
      xres = self._width / segments_x
      yres = self._height / segments_y
      geotransform = [ur_rect.xMinimum(), xres, 0, ur_rect.yMaximum(), 0, -yres]
      if is_grid_point:
        geotransform[0] -= 0.5 * geotransform[1]
        geotransform[3] -= 0.5 * geotransform[5]

    return geotransform

  def center(self):
    return self._center

  def width(self):
    return self._width

  def height(self):
    return self._height

  def rotation(self):
    return self._rotation

  def unrotatedRect(self):
    return self._unrotated_rect

  def geometry(self):
    pts = self.vertices()
    pts.append(pts[0])
    return QgsGeometry.fromPolygon([pts])

  def vertices(self):
    """return vertices of the rect clockwise"""
    rect = self._unrotated_rect
    pts = [QgsPoint(rect.xMinimum(), rect.yMaximum()),
           QgsPoint(rect.xMaximum(), rect.yMaximum()),
           QgsPoint(rect.xMaximum(), rect.yMinimum()),
           QgsPoint(rect.xMinimum(), rect.yMinimum())]

    if self._rotation:
      return [self.rotatePoint(pt, self._rotation, self._center) for pt in pts]

    return pts

  def __repr__(self):
    return "RotatedRect(c:{0}, w:{1}, h:{2}, r:{3})".format(self._center.toString(), self._width, self._height, self._rotation)

    # print coordinates of vertices
    pts = self.verticies()
    return "RotatedRect:" + ",".join(["P{0}({1})".format(x_y[0], x_y[1].toString()) for x_y in enumerate(pts)])
