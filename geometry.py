# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
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
from qgis.core import QgsGeometry, QgsPoint, QgsFeature, QgsSpatialIndex

try:
  from osgeo import ogr
except ImportError:
  import ogr


class Point:
  def __init__(self, x, y, z=0):
    self.x = x
    self.y = y
    self.z = z

  def __eq__(self, other):
    return self.x == other.x and self.y == other.y and self.z == other.z

  def __ne__(self, other):
    return self.x != other.x or self.y != other.y or self.z != other.z


def pointToQgsPoint(point):
  return QgsPoint(point.x, point.y)

def lineToQgsPolyline(line):
  return map(pointToQgsPoint, line)

def polygonToQgsPolygon(polygon):
  return map(lineToQgsPolyline, polygon)


class PointGeometry:
  def __init__(self):
    self.pts = []

  def asList(self):
    return map(lambda pt: [pt.x, pt.y, pt.z], self.pts)

  def toQgsGeometry(self):
    count = len(self.pts)
    if count > 1:
      pts = map(pointToQgsPoint, self.pts)
      return QgsGeometry.fromMultiPoint(pts)

    if count == 1:
      return QgsGeometry.fromPoint(pointToQgsPoint(self.pts[0]))

    return QgsGeometry()

  @staticmethod
  def fromQgsGeometry(geometry, z_func, transform_func):
    geom = PointGeometry()
    pts = geometry.asMultiPoint() if geometry.isMultipart() else [geometry.asPoint()]
    geom.pts = [transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in pts]
    return geom

  @staticmethod
  def fromOgrGeometry25D(geometry, transform_func):
    geomType = geometry.GetGeometryType()

    if geomType == ogr.wkbPoint25D:
      geoms = [geometry]
    elif geomType == ogr.wkbMultiPoint25D:
      geoms = [geometry.GetGeometryRef(i) for i in range(geometry.GetGeometryCount())]
    else:
      return None

    pts = []
    for geom in geoms:
      if hasattr(geom, "GetPoints"):
        pts += geom.GetPoints()
      else:
        pts += [geom.GetPoint(i) for i in range(geom.GetPointCount())]

    point_geom = PointGeometry()
    point_geom.pts = [transform_func(pt[0], pt[1], pt[2]) for pt in pts]
    return point_geom


class LineGeometry:
  def __init__(self):
    self.lines = []

  def asList(self):
    return [map(lambda pt: [pt.x, pt.y, pt.z], line) for line in self.lines]

  def toQgsGeometry(self):
    count = len(self.lines)
    if count > 1:
      lines = map(lineToQgsPolyline, self.lines)
      return QgsGeometry.fromMultiPolyline(lines)

    if count == 1:
      return QgsGeometry.fromPolyline(lineToQgsPolyline(self.lines[0]))

    return QgsGeometry()

  @staticmethod
  def fromQgsGeometry(geometry, z_func, transform_func):
    geom = LineGeometry()
    lines = geometry.asMultiPolyline() if geometry.isMultipart() else [geometry.asPolyline()]
    geom.lines = [[transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in line] for line in lines]
    return geom

  @staticmethod
  def fromOgrGeometry25D(geometry, transform_func):
    geomType = geometry.GetGeometryType()
    if geomType == ogr.wkbLineString25D:
      geoms = [geometry]
    elif geomType == ogr.wkbMultiLineString25D:
      geoms = [geometry.GetGeometryRef(i) for i in range(geometry.GetGeometryCount())]
    else:
      return None

    line_geom = LineGeometry()
    for geom in geoms:
      if hasattr(geom, "GetPoints"):
        pts = geom.GetPoints()
      else:
        pts = [geom.GetPoint(i) for i in range(geom.GetPointCount())]

      points = [transform_func(pt[0], pt[1], pt[2]) for pt in pts]
      line_geom.lines.append(points)

    return line_geom


class PolygonGeometry:
  def __init__(self):
    self.polygons = []
    self.centroids = []
    self.split_polygons = []

  def splitPolygon(self, triMesh):
    """split polygon by TriangleMesh"""
    self.split_polygons = []
    for polygon in triMesh.splitPolygons(self.toQgsGeometry()):
      boundaries = []
      # outer boundary
      points = [Point(pt.x(), pt.y(), 0) for pt in polygon[0]]
      if not GeometryUtils.isClockwise(points):
        points.reverse()    # to clockwise
      boundaries.append(points)

      # inner boundaries
      for boundary in polygon[1:]:
        points = [Point(pt.x(), pt.y(), 0) for pt in boundary]
        if GeometryUtils.isClockwise(points):
          points.reverse()    # to counter-clockwise
        boundaries.append(points)

      self.split_polygons.append(boundaries)

  def asList(self):
    p = []
    for boundaries in self.polygons:
      # outer boundary
      pts = map(lambda pt: [pt.x, pt.y, pt.z], boundaries[0])
      if not GeometryUtils.isClockwise(boundary):
        pts.reverse()   # to clockwise
      b = [pts]

      # inner boundaries
      for boundary in boundaries[1:]:
        pts = map(lambda pt: [pt.x, pt.y, pt.z], boundary)
        if GeometryUtils.isClockwise(boundary):
          pts.reverse()   # to counter-clockwise
        b.append(pts)
      p.append(b)
    return p

  def toQgsGeometry(self):
    count = len(self.polygons)
    if count > 1:
      polys = map(polygonToQgsPolygon, self.polygons)
      return QgsGeometry.fromMultiPolygon(polys)

    if count == 1:
      return QgsGeometry.fromPolygon(polygonToQgsPolygon(self.polygons[0]))

    return QgsGeometry()

  @staticmethod
  def fromQgsGeometry(geometry, z_func, transform_func, calcCentroid=False):

    useCentroidHeight = True
    centroidPerPolygon = True

    polygons = geometry.asMultiPolygon() if geometry.isMultipart() else [geometry.asPolygon()]
    geom = PolygonGeometry()
    if calcCentroid and not centroidPerPolygon:
      pt = geometry.centroid().asPoint()
      centroidHeight = z_func(pt.x(), pt.y())
      geom.centroids.append(transform_func(pt.x(), pt.y(), centroidHeight))

    for polygon in polygons:
      if useCentroidHeight or calcCentroid:
        pt = QgsGeometry.fromPolygon(polygon).centroid().asPoint()
        centroidHeight = z_func(pt.x(), pt.y())
        if calcCentroid and centroidPerPolygon:
          geom.centroids.append(transform_func(pt.x(), pt.y(), centroidHeight))

      if useCentroidHeight:
        z_func = lambda x, y: centroidHeight

      boundaries = []
      # outer boundary
      points = []
      for pt in polygon[0]:
        points.append(transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())))

      if not GeometryUtils.isClockwise(points):
        points.reverse()    # to clockwise
      boundaries.append(points)

      # inner boundaries
      for boundary in polygon[1:]:
        points = [transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in boundary]
        if GeometryUtils.isClockwise(points):
          points.reverse()    # to counter-clockwise
        boundaries.append(points)

      geom.polygons.append(boundaries)

    return geom

#  @staticmethod
#  def fromOgrGeometry25D(geometry, transform_func):
#    pass

class GeometryUtils:

  @classmethod
  def _signedArea(cls, p):
    """Calculates signed area of polygon."""
    area = 0
    for i in range(len(p) - 1):
      area += (p[i].x - p[i + 1].x) * (p[i].y + p[i + 1].y)
    return area / 2

  @classmethod
  def isClockwise(cls, linearRing):
    """Returns whether given linear ring is clockwise."""
    return cls._signedArea(linearRing) < 0


class TriangleMesh:

  # 0 - 3
  # | / |
  # 1 - 2

  def __init__(self, xmin, ymin, xmax, ymax, x_segments, y_segments):
    self.vbands = []
    self.hbands = []
    self.vidx = QgsSpatialIndex()
    self.hidx = QgsSpatialIndex()

    xres = (xmax - xmin) / x_segments
    yres = (ymax - ymin) / y_segments
    self.xmin, self.ymax, self.xres, self.yres = xmin, ymax, xres, yres

    def addVBand(idx, geom):
      f = QgsFeature(idx)
      f.setGeometry(geom)
      self.vbands.append(f)
      self.vidx.insertFeature(f)

    def addHBand(idx, geom):
      f = QgsFeature(idx)
      f.setGeometry(geom)
      self.hbands.append(f)
      self.hidx.insertFeature(f)

    for x in range(x_segments):
      pt0 = QgsPoint(xmin + x * xres, ymax)
      pt1 = QgsPoint(xmin + x * xres, ymin)
      pt2 = QgsPoint(xmin + (x + 1) * xres, ymin)
      pt3 = QgsPoint(xmin + (x + 1) * xres, ymax)
      addVBand(x, QgsGeometry.fromPolygon([[pt0, pt1, pt2, pt3, pt0]]))

    for y in range(y_segments):
      pt0 = QgsPoint(xmin, ymax - y * yres)
      pt1 = QgsPoint(xmin, ymax - (y + 1) * yres)
      pt2 = QgsPoint(xmax, ymax - (y + 1) * yres)
      pt3 = QgsPoint(xmax, ymax - y * yres)
      addHBand(y, QgsGeometry.fromPolygon([[pt0, pt1, pt2, pt3, pt0]]))

  def vSplit(self, geom):
    """split polygon vertically"""
    for idx in self.vidx.intersects(geom.boundingBox()):
      yield idx, geom.intersection(self.vbands[idx].geometry())

  def hIntersects(self, geom):
    """indices of horizontal bands that intersect with geom"""
    for idx in self.hidx.intersects(geom.boundingBox()):
      if geom.intersects(self.hbands[idx].geometry()):
        yield idx

  def splitPolygons(self, geom):
    xmin, ymax, xres, yres = self.xmin, self.ymax, self.xres, self.yres

    for x, vi in self.vSplit(geom):
      for y in self.hIntersects(vi):
        pt0 = QgsPoint(xmin + x * xres, ymax - y * yres)
        pt1 = QgsPoint(xmin + x * xres, ymax - (y + 1) * yres)
        pt2 = QgsPoint(xmin + (x + 1) * xres, ymax - (y + 1) * yres)
        pt3 = QgsPoint(xmin + (x + 1) * xres, ymax - y * yres)
        quad = QgsGeometry.fromPolygon([[pt0, pt1, pt2, pt3, pt0]])
        tris = [[[pt0, pt1, pt3, pt0]], [[pt3, pt1, pt2, pt3]]]

        if geom.contains(quad):
          yield tris[0]
          yield tris[1]
        else:
          for i, tri in enumerate(map(QgsGeometry.fromPolygon, tris)):
            if geom.contains(tri):
              yield tris[i]
            elif geom.intersects(tri):
              poly = geom.intersection(tri)
              if poly.isMultipart():
                for sp in poly.asMultiPolygon():
                  yield sp
              else:
                yield poly.asPolygon()
