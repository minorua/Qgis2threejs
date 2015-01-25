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
from qgis.core import QgsGeometry

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


class PointGeometry:
  def __init__(self):
    self.pts = []

  def asList(self):
    return map(lambda pt: [pt.x, pt.y, pt.z], self.pts)

  @staticmethod
  def fromQgsGeometry(geometry, z_func, transform_func):
    geom = PointGeometry()
    pts = geometry.asMultiPoint() if geometry.isMultipart() else [geometry.asPoint()]
    geom.pts = [transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in pts]
    return geom

  @staticmethod
  def fromWkb25D(wkb, transform_func):
    geom = ogr.CreateGeometryFromWkb(wkb)
    geomType = geom.GetGeometryType()

    if geomType == ogr.wkbPoint25D:
      geoms = [geom]
    elif geomType == ogr.wkbMultiPoint25D:
      geoms = [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
    else:
      geoms = []

    pts = []
    for geom25d in geoms:
      if hasattr(geom25d, "GetPoints"):
        pts += geom25d.GetPoints()
      else:
        pts += [geom25d.GetPoint(i) for i in range(geom25d.GetPointCount())]

    point_geom = PointGeometry()
    point_geom.pts = [transform_func(pt[0], pt[1], pt[2]) for pt in pts]
    return point_geom


class LineGeometry:
  def __init__(self):
    self.lines = []

  def asList(self):
    return [map(lambda pt: [pt.x, pt.y, pt.z], line) for line in self.lines]

  @staticmethod
  def fromQgsGeometry(geometry, z_func, transform_func):
    geom = LineGeometry()
    lines = geometry.asMultiPolyline() if geometry.isMultipart() else [geometry.asPolyline()]
    geom.lines = [[transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in line] for line in lines]
    return geom

  @staticmethod
  def fromWkb25D(wkb, transform_func):
    geom = ogr.CreateGeometryFromWkb(wkb)
    geomType = geom.GetGeometryType()

    if geomType == ogr.wkbLineString25D:
      geoms = [geom]
    elif geomType == ogr.wkbMultiLineString25D:
      geoms = [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
    else:
      geoms = []

    line_geom = LineGeometry()
    for geom25d in geoms:
      if hasattr(geom25d, "GetPoints"):
        pts = geom25d.GetPoints()
      else:
        pts = [geom25d.GetPoint(i) for i in range(geom25d.GetPointCount())]

      points = [transform_func(pt[0], pt[1], pt[2]) for pt in pts]
      line_geom.lines.append(points)

    return line_geom


class PolygonGeometry:
  def __init__(self):
    self.polygons = []
    self.centroids = []
    self.split_polygons = []

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

  @staticmethod
  def fromQgsGeometry(geometry, z_func, transform_func, calcCentroid=False, triMesh=None):

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

    if triMesh is None:
      return geom

    # split polygon for overlay
    for polygon in triMesh.splitPolygon(geometry):
      boundaries = []
      # outer boundary
      points = [transform_func(pt.x(), pt.y(), 0) for pt in polygon[0]]
      if not GeometryUtils.isClockwise(points):
        points.reverse()    # to clockwise
      boundaries.append(points)

      # inner boundaries
      for boundary in polygon[1:]:
        points = [transform_func(pt.x(), pt.y(), 0) for pt in boundary]
        if GeometryUtils.isClockwise(points):
          points.reverse()    # to counter-clockwise
        boundaries.append(points)

      geom.split_polygons.append(boundaries)

    return geom

#  @staticmethod
#  def fromWkb25D(wkb):
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
