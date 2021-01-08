# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MapExtent
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
from qgis.core import QgsPointXY, QgsRectangle, QgsGeometry


class MapExtent:

    def __init__(self, center, width, height, rotation=0):
        """
        args:
          center        -- QgsPointXY
          width, height -- float
          rotation      -- int/float. in degrees counter-clockwise.
        """
        self._center = center
        self._width = width
        self._height = height
        self._rotation = rotation
        self._updateDerived()

    def clone(self):
        return MapExtent(self._center, self._width, self._height, self._rotation)

    def _updateDerived(self):
        self._unrotated_rect = self._unrotatedRect()

    def _unrotatedRect(self):
        center = self._center
        half_width = self._width / 2
        half_height = self._height / 2
        return QgsRectangle(center.x() - half_width, center.y() - half_height,
                            center.x() + half_width, center.y() + half_height)

    @staticmethod
    def rotatePoint(x, y, degrees, origin=None):
        """Rotate point around the origin"""
        if origin:
            x = x - origin.x()
            y = y - origin.y()

        theta = degrees * math.pi / 180
        c = math.cos(theta)
        s = math.sin(theta)

        # rotate counter-clockwise
        xd = x * c - y * s
        yd = x * s + y * c

        if origin:
            return xd + origin.x(), yd + origin.y()
        return xd, yd

    @staticmethod
    def rotateQgsPoint(pt, degrees, origin=None):
        x, y = MapExtent.rotatePoint(pt.x(), pt.y(), degrees, origin)
        return QgsPointXY(x, y)

    def normalizePoint(self, x, y):
        """Normalize given point. In result, lower-left is (0, 0) and upper-right is (1, 1)."""
        if self._rotation:
            x, y = MapExtent.rotatePoint(x, y, -self._rotation, self._center)
        rect = self._unrotated_rect
        return ((x - rect.xMinimum()) / rect.width(),
                (y - rect.yMinimum()) / rect.height())

    def scale(self, s):
        self._width *= s
        self._height *= s
        self._updateDerived()
        return self

    def rotate(self, degrees, origin=None):
        """Rotate the center of extent around the origin
        args:
          degrees -- int/float (counter-clockwise)
          origin  -- QgsPointXY
        """
        self._rotation += degrees
        if origin is None:
            return self
        self._center = MapExtent.rotateQgsPoint(self._center, degrees, origin)
        self._updateDerived()
        return self

    def point(self, nx, ny, y_inverted=False):
        """
        args:
          nx, ny     -- normalized x and y. 0 <= nx <= 1, 0 <= ny <= 1.
          y_inverted -- If True, lower-left is (0, 1) and upper-right is (1, 0).
                        Or else lower-left is (0, 0) and upper-right is (1, 1).
        """
        ur_rect = self._unrotated_rect
        x = ur_rect.xMinimum() + nx * ur_rect.width()
        if y_inverted:
            y = ur_rect.yMaximum() - ny * ur_rect.height()
        else:
            y = ur_rect.yMinimum() + ny * ur_rect.height()
        if self._rotation:
            return self.rotatePoint(x, y, self._rotation, self._center)
        return x, y

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
        return MapExtent(rect.center(), rect.width(), rect.height()).rotate(self._rotation, self._center)

    @staticmethod
    def fromRect(rect):
        return MapExtent(rect.center(), rect.width(), rect.height())

    @staticmethod
    def fromMapSettings(mapSettings, square=False):
        extent = mapSettings.visibleExtent()
        rotation = mapSettings.rotation()
        if rotation == 0:
            w, h = (extent.width(), extent.height())
            if square:
                w = h = max(w, h)
            return MapExtent(extent.center(), w, h)

        mupp = mapSettings.mapUnitsPerPixel()
        canvas_size = mapSettings.outputSize()
        w, h = (canvas_size.width(), canvas_size.height())
        if square:
            w = h = max(w, h)
        return MapExtent(extent.center(), mupp * w, mupp * h, rotation)

    def toMapSettings(self, mapSettings=None):
        if mapSettings is None:
            from qgis.core import QgsMapSettings
            mapSettings = QgsMapSettings()
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
            rx, ry = self.rotatePoint(ur_rect.xMinimum(), ur_rect.yMaximum(), rotation, center)
            res_lr = self._width / segments_x
            res_ul = self._height / segments_y

            theta = rotation * math.pi / 180
            c = math.cos(theta)
            s = math.sin(theta)
            geotransform = [rx, res_lr * c, res_ul * s, ry, res_lr * s, -res_ul * c]
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
        geom = QgsGeometry.fromRect(self._unrotated_rect)
        if self._rotation:
            geom.rotate(-self._rotation, self._center)
        return geom

    def vertices(self):
        """return vertices of the rect clockwise"""
        rect = self._unrotated_rect
        pts = [QgsPointXY(rect.xMinimum(), rect.yMaximum()),
               QgsPointXY(rect.xMaximum(), rect.yMaximum()),
               QgsPointXY(rect.xMaximum(), rect.yMinimum()),
               QgsPointXY(rect.xMinimum(), rect.yMinimum())]

        if self._rotation:
            return [self.rotateQgsPoint(pt, self._rotation, self._center) for pt in pts]

        return pts

    def __repr__(self):
        return "MapExtent(c:{0}, w:{1}, h:{2}, r:{3})".format(self._center.toString(), self._width, self._height, self._rotation)

        # print coordinates of vertices
        pts = self.verticies()
        return "MapExtent:" + ",".join(["P{0}({1})".format(x_y[0], x_y[1].toString()) for x_y in enumerate(pts)])
