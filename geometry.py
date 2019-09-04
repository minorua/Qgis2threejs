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
    QgsPoint, QgsMultiPoint, QgsLineString, QgsMultiLineString, QgsPolygon, QgsMultiPolygon, QgsProject,
    QgsTessellator, QgsWkbTypes)

from .conf import DEBUG_MODE
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

    """No 3D support"""

    def __init__(self):
        self.polygons = []
        self.centroids = []

    def splitPolygon(self, triMesh, z_func):
        """split polygon by TriangleMesh"""
        split_polygons = []
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

            split_polygons.append(boundaries)

        return self.toQgsGeometry(split_polygons)

    def asList(self):
        p = []
        for boundaries in self.polygons:
            # outer boundary
            pts = [[pt.x, pt.y, pt.z] for pt in boundaries[0]]
            b = [pts]

            # inner boundaries
            for boundary in boundaries[1:]:
                pts = [[pt.x, pt.y, pt.z] for pt in boundary]
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

    def toQgsGeometry(self, polygons=None):
        if polygons is None:
            polygons = self.polygons
        count = len(polygons)
        if count > 1:
            polys = [polygonToQgsPolygon(poly) for poly in polygons]
            return QgsGeometry.fromMultiPolygonXY(polys)

        if count == 1:
            return QgsGeometry.fromPolygonXY(polygonToQgsPolygon(polygons[0]))

        return QgsGeometry()

    @classmethod
    def fromQgsGeometry(cls, geometry, z_func, transform_func, useCentroidHeight=True, centroidPerPolygon=False):

        geom = cls()
        polygons = geometry.asMultiPolygon() if geometry.isMultipart() else [geometry.asPolygon()]

        if not centroidPerPolygon:
            pt = geometry.centroid().asPoint()
            centroidHeight = z_func(pt.x(), pt.y())
            geom.centroids.append(transform_func(pt.x(), pt.y(), centroidHeight))

        for polygon in polygons:

            if useCentroidHeight or centroidPerPolygon:
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

                if useCentroidHeight:
                    z_func = (lambda x, y: centroidHeight)

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


class TINGeometry(Geometry):

    def __init__(self):
        self.triangles = []
        self.centroids = []

    def toDict(self, flat=False):
        tris = IndexedTriangles3D()
        for v0, v1, v2 in self.triangles:
            tris.addTriangle(v0, v1, v2)

        if flat:
            v = []
            for pt in tris.vertices:
                v.extend([pt.x, pt.y, pt.z])

            f = []
            for c in tris.faces:
                f.extend(c)

        else:
            v = [[pt.x, pt.y, pt.z] for pt in tris.vertices]
            f = tris.faces

        d = {"triangles": {"v": v, "f": f}}
        if self.centroids:
            d["centroids"] = [[pt.x, pt.y, pt.z] for pt in self.centroids]
        return d

    def toDict2(self, flat=False):
        tris = IndexedTriangles2D()
        for v0, v1, v2 in self.triangles:
            tris.addTriangle(v0, v1, v2)

        if flat:
            v = []
            for pt in tris.vertices:
                v.extend([pt.x, pt.y])

            f = []
            for c in tris.faces:
                f.extend(c)

        else:
            v = [[pt.x, pt.y] for pt in tris.vertices]
            f = tris.faces

        d = {"triangles": {"v": v,"f": f}}
        if self.centroids:
            d["centroids"] = [[pt.x, pt.y] for pt in self.centroids]
        return d

    def toQgsGeometry(self):
        """not implemented yet"""
        pass

    @classmethod
    def fromQgsGeometry(cls, geometry, z_func, transform_func, centroid=False, drop_z=False, ccw2d=False):
        geom = cls()

        if z_func:
            cache = FunctionCacheXY(z_func)
            z_func = cache.func
        else:
            z_func = lambda x, y: 0

        if drop_z:
            g = geometry.get()
            g.dropZValue()
        else:
            g = geometry.constGet()

        if centroid:
            pt = g.centroid()
            geom.centroids.append(transform_func(pt.x(), pt.y(), pt.z() + z_func(pt.x(), pt.y())))

        if isinstance(g, QgsPolygon):
            polygons = [g]
        elif isinstance(g, QgsMultiPolygon):
            polygons = [g.geometryN(i) for i in range(g.numGeometries())]
        else:
            logMessage("PolygonGeometry: {} is not supported yet.".format(type(g).__name__))
            polygons = []

        # triangulation
        tes = QgsTessellator(0, 0, False)
        addPolygon = tes.addPolygon
        for poly in polygons: addPolygon(poly, 0)

        data = tes.data()       # [x0, z0, -y0, x1, z1, -y1, ...]
        # mp = tes.asMultiPolygon()     # not available

        # transform vertices
        if drop_z:
            v_func = lambda x, y, z: transform_func(x, y, z_func(x, y))
        else:
            v_func = lambda x, y, z: transform_func(x, y, z + z_func(x, y))

        vertices = [v_func(x, -my, z) for x, z, my in [data[i:i + 3] for i in range(0, len(data), 3)]]

        if ccw2d:
            # orient triangles to counter-clockwise order
            tris = []
            for v0, v1, v2 in [vertices[i:i + 3] for i in range(0, len(vertices), 3)]:
                if GeometryUtils.isClockwise([v0, v1, v2, v0]):
                    tris.append([v0, v2, v1])
                else:
                    tris.append([v0, v1, v2])
            geom.triangles = tris
        else:
            # use original vertex order
            geom.triangles = [vertices[i:i + 3] for i in range(0, len(vertices), 3)]

        return geom


class FunctionCacheXY:

    def __init__(self, func):
        self._func = func
        self.cache = {}

    def clearCache(self):
        self.cache = {}

    def func(self, x, y):
        xz = self.cache.get(y, {})
        z = xz.get(x)
        if z is None:
            z = self._func(x, y)
            xz[x] = z
            self.cache[y] = xz
        return z


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

    # 0 - 3
    # | / |
    # 1 - 2

    def __init__(self, extent, x_segments, y_segments):

        center = extent.center()
        half_width, half_height = (extent.width() / 2,
                                   extent.height() / 2)
        xmin, ymin = (center.x() - half_width,
                      center.y() - half_height)
        xmax, ymax = (center.x() + half_width,
                      center.y() + half_height)
        xres = (xmax - xmin) / x_segments
        yres = (ymax - ymin) / y_segments

        self.xmin, self.ymax, self.xres, self.yres = (xmin, ymax, xres, yres)

        vbands = []
        hbands = []

        for x in range(x_segments):
            f = QgsFeature(x)
            f.setGeometry(QgsGeometry.fromRect(QgsRectangle(xmin + x * xres, ymin,
                                                            xmin + (x + 1) * xres, ymax)))
            vbands.append(f)

        for y in range(y_segments):
            f = QgsFeature(y)
            f.setGeometry(QgsGeometry.fromRect(QgsRectangle(xmin, ymax - (y + 1) * yres,
                                                            xmax, ymax - y * yres)))
            hbands.append(f)

        self.vbands = vbands
        self.hbands = hbands

        self.vidx = QgsSpatialIndex()
        self.vidx.addFeatures(vbands)

        self.hidx = QgsSpatialIndex()
        self.hidx.addFeatures(hbands)

    def vSplit(self, geom):
        """split polygon vertically"""
        for idx in self.vidx.intersects(geom.boundingBox()):
            geometry = geom.intersection(self.vbands[idx].geometry())
            if geometry:
                yield idx, geometry

    def hIntersects(self, geom):
        """indices of horizontal bands that intersect with geom"""
        for idx in self.hidx.intersects(geom.boundingBox()):
            if geom.intersects(self.hbands[idx].geometry()):
                yield idx

    def splitPolygon(self, geom):
        return QgsGeometry.fromMultiPolygonXY(list(self.splitPolygonA(geom)))

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
                            wkbType = poly.wkbType()
                            if wkbType == QgsWkbTypes.Polygon:
                                yield poly.asPolygon()

                            elif wkbType == QgsWkbTypes.MultiPolygon:
                                for bnd in poly.asMultiPolygon():
                                    yield bnd

                            elif wkbType == QgsWkbTypes.GeometryCollection:
                                for poly2 in poly.asGeometryCollection():
                                    if DEBUG_MODE:
                                        logMessage("A geometry collection was generated. wkbType: {}".format(poly2.wkbType()))

                                    wkbType = poly2.wkbType()
                                    if wkbType == QgsWkbTypes.Polygon:
                                        yield poly2.asPolygon()

                                    elif wkbType == QgsWkbTypes.MultiPolygon:
                                        for bnd in poly2.asMultiPolygon():
                                            yield bnd


class IndexedTriangles2D:

    EMPDICT = {}

    def __init__(self):
        self.vertices = []
        self.faces = []
        self.vidx = {}   # to find whether a vertex already exists: [y][x] = vertex index

    def addTriangle(self, v1, v2, v3):
        vi1 = self._vertexIndex(v1)
        vi2 = self._vertexIndex(v2)
        vi3 = self._vertexIndex(v3)
        self.faces.append([vi1, vi2, vi3])

    def _vertexIndex(self, v):
        vi = self.vidx.get(v.y, self.EMPDICT).get(v.x)
        if vi is not None:
            return vi

        vi = len(self.vertices)
        self.vertices.append(v)

        self.vidx[v.y] = self.vidx.get(v.y, {})
        self.vidx[v.y][v.x] = vi
        return vi


class IndexedTriangles3D:

    EMPDICT = {}

    def __init__(self):
        self.vertices = []
        self.faces = []
        self.vidx = {}   # to find whether a vertex already exists: [z][y][x] = vertex index

    def addTriangle(self, v1, v2, v3):
        vi1 = self._vertexIndex(v1)
        vi2 = self._vertexIndex(v2)
        vi3 = self._vertexIndex(v3)
        self.faces.append([vi1, vi2, vi3])

    def _vertexIndex(self, v):
        vi = self.vidx.get(v.z, self.EMPDICT).get(v.y, self.EMPDICT).get(v.x)
        if vi is not None:
            return vi

        vi = len(self.vertices)
        self.vertices.append(v)

        self.vidx[v.z] = self.vidx.get(v.z, {})
        self.vidx[v.z][v.y] = self.vidx[v.z].get(v.y, {})
        self.vidx[v.z][v.y][v.x] = vi
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

    if combi is None:
        return None

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
