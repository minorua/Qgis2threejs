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
from qgis.core import (
  QgsGeometry, QgsPointXY, QgsRectangle, QgsFeature, QgsSpatialIndex, QgsCoordinateTransform, QgsFeatureRequest,
  QgsPoint, QgsMultiPoint, QgsLineString, QgsMultiLineString, QgsProject)

from .qgis2threejstools import logMessage


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
  return QgsPointXY(point.x, point.y)


def lineToQgsPolyline(line):
  return [pointToQgsPoint(pt) for pt in line]


def polygonToQgsPolygon(polygon):
  return [lineToQgsPolyline(line) for line in polygon]


class Geometry:

  NotUseZM = 0
  UseZ = 1
  UseM = 2


class PointGeometry(Geometry):

  def __init__(self):
    self.pts = []

  def asList(self):
    return [[pt.x, pt.y, pt.z] for pt in self.pts]

  def toQgsGeometry(self):
    count = len(self.pts)
    if count > 1:
      pts = [pointToQgsPoint(pt) for pt in self.pts]
      return QgsGeometry.fromMultiPointXY(pts)

    if count == 1:
      return QgsGeometry.fromPointXY(pointToQgsPoint(self.pts[0]))

    return QgsGeometry()

  @classmethod
  def fromQgsGeometry(cls, geometry, z_func, transform_func, useZM=Geometry.NotUseZM):
    geom = cls()
    if useZM == Geometry.NotUseZM:
      pts = geometry.asMultiPoint() if geometry.isMultipart() else [geometry.asPoint()]
      geom.pts = [transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in pts]

    else:
      g = geometry.constGet()
      if isinstance(g, QgsPoint):
        pts = [g]
      elif isinstance(g, QgsMultiPoint):
        pts = [g.geometryN(i) for i in range(g.numGeometries())]
      else:
        logMessage("Unknown point geometry type: " + type(g))
        pts = []

      if useZM == Geometry.UseZ:
        geom.pts = [transform_func(pt.x(), pt.y(), pt.z() + z_func(pt.x(), pt.y())) for pt in pts]

      else:   # UseM
        geom.pts = [transform_func(pt.x(), pt.y(), pt.m() + z_func(pt.x(), pt.y())) for pt in pts]

    return geom


class LineGeometry(Geometry):

  def __init__(self):
    self.lines = []

  def asList(self):
    return [[[pt.x, pt.y, pt.z] for pt in line] for line in self.lines]

  def asList2(self):
    return [[[pt.x, pt.y] for pt in line] for line in self.lines]

  def toQgsGeometry(self):
    count = len(self.lines)
    if count > 1:
      lines = [lineToQgsPolyline(line) for line in self.lines]
      return QgsGeometry.fromMultiPolylineXY(lines)

    if count == 1:
      return QgsGeometry.fromPolylineXY(lineToQgsPolyline(self.lines[0]))

    return QgsGeometry()

  @classmethod
  def fromQgsGeometry(cls, geometry, z_func, transform_func, useZM=Geometry.NotUseZM):
    geom = cls()
    if useZM == Geometry.NotUseZM:
      lines = geometry.asMultiPolyline() if geometry.isMultipart() else [geometry.asPolyline()]
      geom.lines = [[transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in line] for line in lines]

    else:
      g = geometry.constGet()
      if isinstance(g, QgsLineString):
        lines = [g.points()]
      elif isinstance(g, QgsMultiLineString):
        lines = [g.geometryN(i).points() for i in range(g.numGeometries())]
      else:
        logMessage("Unknown line geometry type: " + type(g))
        lines = []

      if useZM == Geometry.UseZ:
        geom.lines = [[transform_func(pt.x(), pt.y(), pt.z() + z_func(pt.x(), pt.y())) for pt in line] for line in lines]

      else:   # UseM
        geom.lines = [[transform_func(pt.x(), pt.y(), pt.m() + z_func(pt.x(), pt.y())) for pt in line] for line in lines]

    return geom


class PolygonGeometry(Geometry):

  def __init__(self):
    self.polygons = []
    self.centroids = []
    self.split_polygons = []

  def splitPolygon(self, triMesh, z_func):
    """split polygon by TriangleMesh"""
    self.split_polygons = []
    for polygon in triMesh.splitPolygonA(self.toQgsGeometry()):
      boundaries = []
      # outer boundary
      points = [Point(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in polygon[0]]
      if not GeometryUtils.isClockwise(points):
        points.reverse()    # to clockwise
      boundaries.append(points)

      # inner boundaries
      for boundary in polygon[1:]:
        points = [Point(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in boundary]
        if GeometryUtils.isClockwise(points):
          points.reverse()    # to counter-clockwise
        boundaries.append(points)

      self.split_polygons.append(boundaries)

  def asList(self):
    p = []
    for boundaries in self.polygons:
      # outer boundary
      pts = [[pt.x, pt.y, pt.z] for pt in boundaries[0]]
      if not GeometryUtils.isClockwise(boundaries[0]):
        pts.reverse()   # to clockwise
      b = [pts]

      # inner boundaries
      for boundary in boundaries[1:]:
        pts = [[pt.x, pt.y, pt.z] for pt in boundary]
        if GeometryUtils.isClockwise(boundary):
          pts.reverse()   # to counter-clockwise
        b.append(pts)
      p.append(b)
    return p

  def asList2(self):
    p = []
    for boundaries in self.polygons:
      b = []
      for boundary in boundaries:
        b.append([[pt.x, pt.y] for pt in boundary])
      p.append(b)
    return p

  def toQgsGeometry(self):
    count = len(self.polygons)
    if count > 1:
      polys = [polygonToQgsPolygon(poly) for poly in self.polygons]
      return QgsGeometry.fromMultiPolygonXY(polys)

    if count == 1:
      return QgsGeometry.fromPolygonXY(polygonToQgsPolygon(self.polygons[0]))

    return QgsGeometry()

  #TODO: [Polygon z/m support]
  @classmethod
  def fromQgsGeometry(cls, geometry, z_func, transform_func, useCentroidHeight=True, centroidPerPolygon=False):

    polygons = geometry.asMultiPolygon() if geometry.isMultipart() else [geometry.asPolygon()]
    geom = cls()
    if not centroidPerPolygon:
      pt = geometry.centroid().asPoint()
      centroidHeight = z_func(pt.x(), pt.y())
      geom.centroids.append(transform_func(pt.x(), pt.y(), centroidHeight))

    for polygon in polygons:
      centroid = QgsGeometry.fromPolygonXY(polygon).centroid()
      if centroid is None:
        centroidHeight = 0
        if centroidPerPolygon:
          geom.centroids.append(transform_func(0, 0, 0))
      else:
        pt = centroid.asPoint()
        centroidHeight = z_func(pt.x(), pt.y())
        if centroidPerPolygon:
          geom.centroids.append(transform_func(pt.x(), pt.y(), centroidHeight))

      z_func2 = (lambda x, y: centroidHeight) if useCentroidHeight else z_func

      boundaries = []
      # outer boundary
      points = []
      for pt in polygon[0]:
        points.append(transform_func(pt.x(), pt.y(), z_func2(pt.x(), pt.y())))

      if not GeometryUtils.isClockwise(points):
        points.reverse()    # to clockwise
      boundaries.append(points)

      # inner boundaries
      for boundary in polygon[1:]:
        points = [transform_func(pt.x(), pt.y(), z_func2(pt.x(), pt.y())) for pt in boundary]
        if GeometryUtils.isClockwise(points):
          points.reverse()    # to counter-clockwise
        boundaries.append(points)

      geom.polygons.append(boundaries)

    return geom


class GeometryUtils:

  @staticmethod
  def _signedArea(p):
    """Calculates signed area of polygon."""
    area = 0
    for i in range(len(p) - 1):
      area += (p[i].x - p[i + 1].x) * (p[i].y + p[i + 1].y)
    return area / 2

  @staticmethod
  def isClockwise(linearRing):
    """Returns whether given linear ring is clockwise."""
    return GeometryUtils._signedArea(linearRing) < 0


class TriangleMesh:
  #TODO: [Overlay] rotated map support

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
      addVBand(x, QgsGeometry.fromRect(QgsRectangle(xmin + x * xres, ymin, xmin + (x + 1) * xres, ymax)))

    for y in range(y_segments):
      addHBand(y, QgsGeometry.fromRect(QgsRectangle(xmin, ymax - (y + 1) * yres, xmax, ymax - y * yres)))

  def vSplit(self, geom):
    """split polygon vertically"""
    for idx in self.vidx.intersects(geom.boundingBox()):
      yield idx, geom.intersection(self.vbands[idx].geometry())

  def hIntersects(self, geom):
    """indices of horizontal bands that intersect with geom"""
    for idx in self.hidx.intersects(geom.boundingBox()):
      if geom.intersects(self.hbands[idx].geometry()):
        yield idx

  def splitPolygon(self, geom):
    xmin, ymax, xres, yres = self.xmin, self.ymax, self.xres, self.yres

    polygons = []
    for x, vi in self.vSplit(geom):
      for y in self.hIntersects(vi):
        pt0 = QgsPointXY(xmin + x * xres, ymax - y * yres)
        pt1 = QgsPointXY(xmin + x * xres, ymax - (y + 1) * yres)
        pt2 = QgsPointXY(xmin + (x + 1) * xres, ymax - (y + 1) * yres)
        pt3 = QgsPointXY(xmin + (x + 1) * xres, ymax - y * yres)
        quad = QgsGeometry.fromPolygonXY([[pt0, pt1, pt2, pt3, pt0]])
        tris = [[[pt0, pt1, pt3, pt0]], [[pt3, pt1, pt2, pt3]]]

        if geom.contains(quad):
          polygons += tris
        else:
          for i, tri in enumerate(map(QgsGeometry.fromPolygonXY, tris)):
            if geom.contains(tri):
              polygons.append(tris[i])
            elif geom.intersects(tri):
              poly = geom.intersection(tri)
              if poly.isMultipart():
                polygons += poly.asMultiPolygon()
              else:
                polygons.append(poly.asPolygon())
    return QgsGeometry.fromMultiPolygonXY(polygons)

  def splitPolygonA(self, geom):
    xmin, ymax, xres, yres = self.xmin, self.ymax, self.xres, self.yres

    for x, vi in self.vSplit(geom):
      for y in self.hIntersects(vi):
        pt0 = QgsPointXY(xmin + x * xres, ymax - y * yres)
        pt1 = QgsPointXY(xmin + x * xres, ymax - (y + 1) * yres)
        pt2 = QgsPointXY(xmin + (x + 1) * xres, ymax - (y + 1) * yres)
        pt3 = QgsPointXY(xmin + (x + 1) * xres, ymax - y * yres)
        quad = QgsGeometry.fromPolygonXY([[pt0, pt1, pt2, pt3, pt0]])
        tris = [[[pt0, pt1, pt3, pt0]], [[pt3, pt1, pt2, pt3]]]

        if geom.contains(quad):
          yield tris[0]
          yield tris[1]
        else:
          for i, tri in enumerate(map(QgsGeometry.fromPolygonXY, tris)):
            if geom.contains(tri):
              yield tris[i]
            elif geom.intersects(tri):
              poly = geom.intersection(tri)
              if poly.isMultipart():
                for sp in poly.asMultiPolygon():
                  yield sp
              else:
                yield poly.asPolygon()


class Triangles:

  def __init__(self):
    self.vertices = []
    self.faces = []
    self.vdict = {}   # dict to find whether a vertex already exists: [y][x] = vertex index

  def addTriangle(self, v1, v2, v3):
    vi1 = self._vertexIndex(v1)
    vi2 = self._vertexIndex(v2)
    vi3 = self._vertexIndex(v3)
    self.faces.append([vi1, vi2, vi3])

  def _vertexIndex(self, v):
    x_dict = self.vdict.get(v.y)
    if x_dict:
      vi = x_dict.get(v.x)
      if vi is not None:
        return vi
    vi = len(self.vertices)
    self.vertices.append(v)
    if x_dict:
      x_dict[v.x] = vi
    else:
      self.vdict[v.y] = {v.x: vi}
    return vi


def dissolvePolygonsOnCanvas(settings, layer):
  """dissolve polygons of the layer and clip the dissolution with base extent"""
  baseExtent = settings.baseExtent
  baseExtentGeom = baseExtent.geometry()
  rotation = baseExtent.rotation()
  transform = QgsCoordinateTransform(layer.crs(), settings.crs, QgsProject.instance())

  combi = None
  request = QgsFeatureRequest()
  request.setFilterRect(transform.transformBoundingBox(baseExtent.boundingBox(), QgsCoordinateTransform.ReverseTransform))
  for f in layer.getFeatures(request):
    geometry = f.geometry()
    if geometry is None:
      logMessage("null geometry skipped")
      continue

    # coordinate transformation - layer crs to project crs
    geom = QgsGeometry(geometry)
    if geom.transform(transform) != 0:
      logMessage("Failed to transform geometry")
      continue

    # check if geometry intersects with the base extent (rotated rect)
    if rotation and not baseExtentGeom.intersects(geom):
      continue

    if combi:
      combi = combi.combine(geom)
    else:
      combi = geom

  # clip geom with slightly smaller extent than base extent
  # to make sure that the clipped polygon stays within the base extent
  geom = combi.intersection(baseExtent.clone().scale(0.999999).geometry())
  if geom is None:
    return None

  # check if geometry is empty
  if geom.isEmpty():
    logMessage("empty geometry")
    return None

  return geom
