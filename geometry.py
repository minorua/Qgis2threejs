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
from math import ceil, floor
from qgis.core import (
    QgsGeometry, QgsPointXY, QgsRectangle, QgsFeature, QgsSpatialIndex, QgsCoordinateTransform, QgsFeatureRequest,
    QgsPoint, QgsMultiPoint, QgsLineString, QgsMultiLineString, QgsPolygon, QgsMultiPolygon, QgsProject,
    QgsTessellator, QgsVertexId, QgsWkbTypes)

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


class VectorGeometry:

    NotUseZM = 0
    UseZ = 1
    UseM = 2

    @classmethod
    def singleGeometriesXY(cls, geom):
        return []

    @classmethod
    def singleGeometries(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""
        logMessage("{}: {} type is not supported yet.".format(cls.__name__, type(geom).__name__))
        return []


class PointGeometry(VectorGeometry):

    def __init__(self):
        self.pts = []

    def toList(self):
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
    def fromQgsGeometry(cls, geometry, z_func, transform_func, useZM=VectorGeometry.NotUseZM):
        geom = cls()
        if useZM == VectorGeometry.NotUseZM:
            pts = cls.singleGeometriesXY(geometry)
            geom.pts = [transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in pts]

        else:
            pts = cls.singleGeometries(geometry.constGet())
            if useZM == VectorGeometry.UseZ:
                geom.pts = [transform_func(pt.x(), pt.y(), pt.z() + z_func(pt.x(), pt.y())) for pt in pts]

            else:   # UseM
                geom.pts = [transform_func(pt.x(), pt.y(), pt.m() + z_func(pt.x(), pt.y())) for pt in pts]

        return geom

    @classmethod
    def singleGeometriesXY(cls, geom):
        """geom: a QgsGeometry object"""
        wt = geom.wkbType()
        if wt == QgsWkbTypes.GeometryCollection:
            geoms = []
            for g in geom.asGeometryCollection():
                geoms.extend(cls.singleGeometriesXY(g))
            return geoms

        if QgsWkbTypes.singleType(QgsWkbTypes.flatType(wt)) == QgsWkbTypes.Point:
            return geom.asMultiPoint() if geom.isMultipart() else [geom.asPoint()]

        return []

    @classmethod
    def singleGeometries(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""

        if isinstance(geom, QgsPoint):
            return [geom]

        if isinstance(geom, QgsMultiPoint):
            return [geom.geometryN(i) for i in range(geom.numGeometries())]

        return super().singleGeometries(geom)


class LineGeometry(VectorGeometry):

    def __init__(self):
        self.lines = []

    def toList(self):
        return [[[pt.x, pt.y, pt.z] for pt in line] for line in self.lines]

    def toList2(self):
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
    def fromQgsGeometry(cls, geometry, z_func, transform_func, useZM=VectorGeometry.NotUseZM):
        if z_func is None:
            z_func = lambda x, y: 0

        geom = cls()
        if useZM == VectorGeometry.NotUseZM:
            lines = cls.singleGeometriesXY(geometry)
            geom.lines = [[transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in line] for line in lines]

        else:
            lines = cls.singleGeometries(geometry.constGet())
            if useZM == VectorGeometry.UseZ:
                geom.lines = [[transform_func(pt.x(), pt.y(), pt.z() + z_func(pt.x(), pt.y())) for pt in line] for line in lines]

            else:   # UseM
                geom.lines = [[transform_func(pt.x(), pt.y(), pt.m() + z_func(pt.x(), pt.y())) for pt in line] for line in lines]

        return geom

    @classmethod
    def singleGeometriesXY(cls, geom):
        """geom: a QgsGeometry object"""
        wt = geom.wkbType()
        if wt == QgsWkbTypes.GeometryCollection:
            geoms = []
            for g in geom.asGeometryCollection():
                geoms.extend(cls.singleGeometriesXY(g))
            return geoms

        if QgsWkbTypes.singleType(QgsWkbTypes.flatType(wt)) == QgsWkbTypes.LineString:
            return geom.asMultiPolyline() if geom.isMultipart() else [geom.asPolyline()]

        return []

    @classmethod
    def singleGeometries(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""

        if isinstance(geom, QgsLineString):
            return [geom.points()]

        if isinstance(geom, QgsMultiLineString):
            return [geom.geometryN(i).points() for i in range(geom.numGeometries())]

        return super().singleGeometries(geom)


class PolygonGeometry(VectorGeometry):

    """No z value support. Used with Extruded and Overlay (absolute)"""

    def __init__(self):
        self.polygons = []
        self.centroids = []

    def splitPolygon(self, grid, z_func):
        """split polygon by triangular grid"""
        split_polygons = []
        for polygon in grid.splitPolygonA(self.toQgsGeometry()):
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

    def toList(self):
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

    def toList2(self):
        p = []
        for boundaries in self.polygons:
            b = []
            for boundary in boundaries:
                b.append([[pt.x, pt.y] for pt in boundary])
            p.append(b)
        return p

    def toLineGeometryList(self):
        lines = []
        for poly in self.polygons:
            line = LineGeometry()
            line.lines = poly
            lines.append(line)
        return lines

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

        if not centroidPerPolygon:
            pt = geometry.centroid().asPoint()
            centroidHeight = z_func(pt.x(), pt.y())
            geom.centroids.append(transform_func(pt.x(), pt.y(), centroidHeight))

        for polygon in cls.singleGeometriesXY(geometry):

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

    @classmethod
    def singleGeometriesXY(cls, geom):
        """geom: a QgsGeometry object"""
        wt = geom.wkbType()
        if wt == QgsWkbTypes.GeometryCollection:
            geoms = []
            for g in geom.asGeometryCollection():
                geoms.extend(cls.singleGeometriesXY(g))
            return geoms

        if QgsWkbTypes.singleType(QgsWkbTypes.flatType(wt)) == QgsWkbTypes.Polygon:
            return geom.asMultiPolygon() if geom.isMultipart() else [geom.asPolygon()]

        return []

    @classmethod
    def singleGeometries(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""

        if isinstance(geom, QgsPolygon):
            return [geom]

        if isinstance(geom, QgsMultiPolygon):
            return [geom.geometryN(i) for i in range(geom.numGeometries())]

        return super().singleGeometries(geom)


class TINGeometry(PolygonGeometry):

    """Used with Polygon and Overlay (relative to DEM)"""

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
            d["centroids"] = [[pt.x, pt.y, pt.z if pt.z == pt.z else 0] for pt in self.centroids]
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

    @classmethod
    def fromQgsGeometry(cls, geometry, z_func, transform_func, centroid=True, z_func_cntr=None,
                        drop_z=False, ccw2d=False, use_z_func_cache=False):
        geom = cls()

        if z_func:
            if use_z_func_cache:
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
            if z_func_cntr is None:
                # use z coordinate of first vertex (until QgsAbstractGeometry supports z coordinate of centroid)
                z_func_cntr = lambda x, y: g.vertexAt(QgsVertexId(0, 0, 0)).z()

            pt = geometry.centroid().asPoint()
            geom.centroids.append(transform_func(pt.x(), pt.y(), z_func_cntr(pt.x(), pt.y())))

        # triangulation
        tes = QgsTessellator(0, 0, False)
        addPolygon = tes.addPolygon
        for poly in cls.singleGeometries(g): addPolygon(poly, 0)

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
    def _signedAreaA(p):
        """Calculates signed area of polygon."""
        area = 0
        for i in range(len(p) - 1):
            area += (p[i].x() - p[i + 1].x()) * (p[i].y() + p[i + 1].y())
        return area / 2

    @staticmethod
    def isClockwise(linearRing):
        """Returns whether given linear ring is clockwise."""
        if isinstance(linearRing[0], Point):
            return GeometryUtils._signedArea(linearRing) < 0
        else:
            return GeometryUtils._signedAreaA(linearRing) < 0


class GridGeometry:

    """
    Triangular grid geometry
    """

    def __init__(self, extent, x_segments, y_segments, values=None):
        self.extent = extent
        self.x_segments = x_segments
        self.y_segments = y_segments
        self.values = values

        center = extent.center()
        half_width, half_height = (extent.width() / 2,
                                   extent.height() / 2)
        self.xmin, self.ymin = (center.x() - half_width,
                                center.y() - half_height)
        self.xmax, self.ymax = (center.x() + half_width,
                                center.y() + half_height)
        self.xres = extent.width() / x_segments
        self.yres = extent.height() / y_segments

        self.vbands = self.hbands = None

    def setupBands(self):
        xmin, ymin, xmax, ymax = (self.xmin, self.ymin, self.xmax, self.ymax)
        xres, yres = (self.xres, self.yres)

        vbands = []
        hbands = []

        for x in range(self.x_segments):
            f = QgsFeature(x)
            f.setGeometry(QgsGeometry.fromRect(QgsRectangle(xmin + x * xres, ymin,
                                                            xmin + (x + 1) * xres, ymax)))
            vbands.append(f)

        for y in range(self.y_segments):
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

    def splitPolygonXY(self, geom):
        return QgsGeometry.fromMultiPolygonXY(list(self._splitPolygon(geom)))

    def splitPolygon(self, geom):
        polygons = QgsMultiPolygon()
        for poly in self._splitPolygon(geom):
            bnd = QgsLineString()
            for pt in poly[0]:
                bnd.addVertex(QgsPoint(pt.x(), pt.y(), self.valueOnSurface(pt.x(), pt.y()) or 0))

            p = QgsPolygon()
            p.setExteriorRing(bnd)
            polygons.addGeometry(p)

        return QgsGeometry(polygons)

    def _splitPolygon(self, geom):
        if self.vbands is None:
            self.setupBands()

        xmin, ymax, xres, yres = (self.xmin, self.ymax, self.xres, self.yres)

        for x, vi in self.vSplit(geom):
            for y in self.hIntersects(vi):
                # 0 - 1
                # | / |
                # 2 - 3
                v0 = QgsPointXY(xmin + x * xres, ymax - y * yres)
                v1 = QgsPointXY(xmin + (x + 1) * xres, ymax - y * yres)
                v2 = QgsPointXY(xmin + x * xres, ymax - (y + 1) * yres)
                v3 = QgsPointXY(xmin + (x + 1) * xres, ymax - (y + 1) * yres)
                quad = QgsGeometry.fromPolygonXY([[v0, v2, v3, v1, v0]])
                tris = [[[v0, v2, v1, v0]], [[v1, v2, v3, v1]]]

                if geom.contains(quad):
                    yield tris[0]
                    yield tris[1]
                else:
                    for i, tri in enumerate(map(QgsGeometry.fromPolygonXY, tris)):
                        if geom.contains(tri):
                            yield tris[i]
                        elif geom.intersects(tri):
                            for poly in PolygonGeometry.singleGeometriesXY(geom.intersection(tri)):
                                if GeometryUtils.isClockwise(poly[0]):
                                    poly[0].reverse()         # to CCW
                                yield poly

    def segmentizeBoundaries(self, geom):
        """geom: QgsGeometry (polygon or multi-polygon)"""

        xmin, ymax = (self.xmin, self.ymax)
        xres, yres = (self.xres, self.yres)
        z_func = self.valueOnSurface

        polys = []
        for polygon in PolygonGeometry.singleGeometriesXY(geom):
            rings = QgsMultiLineString()
            for i, bnd in enumerate(polygon):
                if GeometryUtils.isClockwise(bnd) ^ (i > 0):   # xor
                    bnd.reverse()       # outer boundary should be ccw. inner boundaries should be cw.

                ring = QgsLineString()

                v = bnd[0]     # QgsPointXY
                x0, y0 = (v.x(), v.y())
                nx0 = (x0 - xmin) / xres
                ny0 = (ymax - y0) / yres
                ns0 = abs(ny0 + nx0)

                for v in bnd[1:]:
                    x1, y1 = (v.x(), v.y())
                    nx1 = (x1 - xmin) / xres
                    ny1 = (ymax - y1) / yres
                    ns1 = abs(ny1 + nx1)

                    p = set([0])
                    for v0, v1 in [[nx0, nx1], [ny0, ny1], [ns0, ns1]]:
                        k = ceil(min(v0, v1))
                        n = floor(max(v0, v1))
                        for j in range(k, n + 1):
                            p.add((j - v0) / (v1 - v0))

                    if 1 in p:
                        p.remove(1)

                    for m in sorted(p):
                        x = x0 + (x1 - x0) * m
                        y = y0 + (y1 - y0) * m
                        ring.addVertex(QgsPoint(x, y, z_func(x, y)))

                    x0, y0 = (x1, y1)
                    nx0, ny0, ns0 = (nx1, ny1, ns1)

                ring.addVertex(QgsPoint(x0, y0, z_func(x0, y0)))    # last vertex
                rings.addGeometry(ring)
            polys.append(QgsGeometry(rings))
        return polys

    def value(self, x, y):
        return self.values[x + y * (self.x_segments + 1)]

    def valueOnSurface(self, x, y):
        pt = self.extent.normalizePoint(x, y)       # bottom-left corner is (0, 0), top-right is (1. 1)
        if pt.x() < 0 or 1 < pt.x() or pt.y() < 0 or 1 < pt.y():
            return None

        mx = pt.x() * self.x_segments
        my = (1 - pt.y()) * self.y_segments     # inverted. top is 0.
        mx0 = floor(mx)
        my0 = floor(my)
        sdx = mx - mx0
        sdy = my - my0

        if mx0 == self.x_segments:  # on right edge
            mx0 -= 1
            sdx = 1

        if my0 == self.y_segments:  # on bottom edge
            my0 -= 1
            sdy = 1

        z0 = self.value(mx0, my0)
        z1 = self.value(mx0 + 1, my0)
        z2 = self.value(mx0, my0 + 1)
        z3 = self.value(mx0 + 1, my0 + 1)

        if sdx <= sdy:
            return z0 + (z1 - z0) * sdx + (z2 - z0) * sdy
        return z3 + (z2 - z3) * (1 - sdx) + (z1 - z3) * (1 - sdy)


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
