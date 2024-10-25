# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from math import ceil, floor
from qgis.core import (
    QgsGeometry, QgsPointXY, QgsRectangle, QgsFeature, QgsSpatialIndex, QgsCoordinateTransform, QgsFeatureRequest,
    QgsPoint, QgsMultiPoint, QgsLineString, QgsMultiLineString, QgsPolygon, QgsMultiPolygon, QgsGeometryCollection,
    QgsProject, QgsTessellator, QgsVertexId, QgsWkbTypes)

from .earcut import earcut

from .utils import logMessage


class VectorGeometry:

    NotUseZM = 0
    UseZ = 1
    UseM = 2

    @classmethod
    def nestedPointXYList(cls, geom):
        if geom.wkbType() == QgsWkbTypes.GeometryCollection:
            pts = []
            for g in geom.asGeometryCollection():
                pts.extend(cls.nestedPointXYList(g))
            return pts

        return []

    @classmethod
    def nestedPointList(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""
        if isinstance(geom, QgsGeometryCollection):
            g = []
            for i in range(geom.numGeometries()):
                g.extend(cls.nestedPointList(geom.geometryN(i)))
            return g

        logMessage("{}: {} type is not supported yet.".format(cls.__name__, type(geom).__name__), warning=True)
        return []

    @classmethod
    def singleGeometries(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""
        if isinstance(geom, QgsGeometryCollection):
            g = []
            for i in range(geom.numGeometries()):
                g.extend(cls.singleGeometries(geom.geometryN(i)))
            return g

        logMessage("{}: {} type is not supported yet.".format(cls.__name__, type(geom).__name__), warning=True)
        return []


class PointGeometry(VectorGeometry):

    def __init__(self):
        self.pts = []

    def toList(self):
        return self.pts

    def toList2(self):
        return [[x, y] for x, y, z in self.pts]

    def toQgsGeometry(self):
        count = len(self.pts)
        if count > 1:
            pts = [QgsPoint(x, y) for x, y, z in self.pts]
            return QgsGeometry.fromMultiPointXY(pts)

        if count == 1:
            x, y, z = self.pts[0]
            return QgsGeometry.fromPointXY(QgsPoint(x, y))

        return QgsGeometry()

    @classmethod
    def fromQgsGeometry(cls, geometry, z_func, transform_func, useZM=VectorGeometry.NotUseZM):
        geom = cls()
        if useZM == VectorGeometry.NotUseZM:
            pts = cls.nestedPointXYList(geometry)
            geom.pts = [transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in pts]

        else:
            pts = cls.nestedPointList(geometry.constGet())
            if useZM == VectorGeometry.UseZ:
                geom.pts = [transform_func(pt.x(), pt.y(), pt.z() + z_func(pt.x(), pt.y())) for pt in pts]

            else:   # UseM
                geom.pts = [transform_func(pt.x(), pt.y(), pt.m() + z_func(pt.x(), pt.y())) for pt in pts]

        return geom

    @classmethod
    def nestedPointXYList(cls, geom):
        """geom: a QgsGeometry object"""
        if QgsWkbTypes.singleType(QgsWkbTypes.flatType(geom.wkbType())) == QgsWkbTypes.Point:
            return geom.asMultiPoint() if geom.isMultipart() else [geom.asPoint()]

        return super().nestedPointXYList(geom)

    @classmethod
    def nestedPointList(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""
        if isinstance(geom, QgsPoint):
            return [geom]

        if isinstance(geom, QgsMultiPoint):
            return [geom.geometryN(i) for i in range(geom.numGeometries())]

        return super().nestedPointList(geom)

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

    def toList(self, flat=False):
        if flat:
            a = []
            for line in self.lines:
                v = []
                for pt in line:
                    v.extend(pt)
                a.append(v)
            return a
        else:
            return self.lines

    def toList2(self):
        return [[[x, y] for x, y, z in line] for line in self.lines]

    def toQgsGeometry(self):
        count = len(self.lines)
        if count > 1:
            lines = [[QgsPointXY(x, y) for x, y, z in line] for line in self.lines]
            return QgsGeometry.fromMultiPolylineXY(lines)

        if count == 1:
            pts = [QgsPointXY(x, y) for x, y, z in self.lines[0]]
            return QgsGeometry.fromPolylineXY(pts)

        return QgsGeometry()

    @classmethod
    def fromQgsGeometry(cls, geometry, z_func, transform_func, useZM=VectorGeometry.NotUseZM):
        if z_func is None:
            z_func = lambda x, y: 0

        geom = cls()
        if useZM == VectorGeometry.NotUseZM:
            lines = cls.nestedPointXYList(geometry)
            geom.lines = [[transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in line] for line in lines]

        else:
            lines = cls.nestedPointList(geometry.constGet())
            if useZM == VectorGeometry.UseZ:
                geom.lines = [[transform_func(pt.x(), pt.y(), pt.z() + z_func(pt.x(), pt.y())) for pt in line] for line in lines]

            else:   # UseM
                geom.lines = [[transform_func(pt.x(), pt.y(), pt.m() + z_func(pt.x(), pt.y())) for pt in line] for line in lines]

        return geom

    @classmethod
    def nestedPointXYList(cls, geom):
        """geom: a QgsGeometry object"""
        if QgsWkbTypes.singleType(QgsWkbTypes.flatType(geom.wkbType())) == QgsWkbTypes.LineString:
            return geom.asMultiPolyline() if geom.isMultipart() else [geom.asPolyline()]

        return super().nestedPointXYList(geom)

    @classmethod
    def nestedPointList(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""
        if isinstance(geom, QgsLineString):
            return [geom.points()]

        if isinstance(geom, QgsMultiLineString):
            return [geom.geometryN(i).points() for i in range(geom.numGeometries())]

        return super().nestedPointList(geom)

    @classmethod
    def singleGeometries(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""
        if isinstance(geom, QgsLineString):
            return [geom]

        if isinstance(geom, QgsMultiLineString):
            return [geom.geometryN(i) for i in range(geom.numGeometries())]

        return super().singleGeometries(geom)


class PolygonGeometry(VectorGeometry):

    """Used with Extruded and Overlay (absolute)"""

    def __init__(self):
        self.polygons = []
        self.centroids = []

    def toList(self):
        return self.polygons

    def toList2(self):
        return [[[[x, y] for x, y, z in bnd] for bnd in poly] for poly in self.polygons]

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
            polys = [[[QgsPointXY(x, y) for x, y, z in bnd] for bnd in poly] for poly in polygons]
            return QgsGeometry.fromMultiPolygonXY(polys)

        if count == 1:
            poly = [[QgsPointXY(x, y) for x, y, z in bnd] for bnd in polygons[0]]
            return QgsGeometry.fromPolygonXY(poly)

        return QgsGeometry()

    @classmethod
    def fromQgsGeometry(cls, geometry, z_func, transform_func, useCentroidHeight=True, centroidPerPolygon=False):

        geom = cls()

        if not centroidPerPolygon:
            pt = geometry.centroid().asPoint()
            centroidHeight = z_func(pt.x(), pt.y())
            geom.centroids.append(transform_func(pt.x(), pt.y(), centroidHeight))

        for polygon in cls.nestedPointXYList(geometry):

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

            bnds = []
            for i, bnd in enumerate(polygon):
                pts = [transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y())) for pt in bnd]
                if GeometryUtils.isClockwise(pts) ^ i == 0:
                    pts.reverse()    # outer boundary to clockwise and inner boundaries to counter-clockwise
                bnds.append(pts)

            geom.polygons.append(bnds)

        return geom

    @classmethod
    def nestedPointXYList(cls, geom):
        """geom: a QgsGeometry object"""
        if QgsWkbTypes.singleType(QgsWkbTypes.flatType(geom.wkbType())) == QgsWkbTypes.Polygon:
            return geom.asMultiPolygon() if geom.isMultipart() else [geom.asPolygon()]

        return super().nestedPointXYList(geom)

    @classmethod
    def nestedPointList(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""
        if isinstance(geom, QgsPolygon):
            rings = [geom.exteriorRing().points()]
            rings += [geom.interiorRing(i).points() for i in range(geom.numInteriorRings())]
            return [rings]

        if isinstance(geom, QgsMultiPolygon):
            polys = []
            for i in range(geom.numGeometries()):
                g = geom.geometryN(i)
                rings = [g.exteriorRing().points()]
                rings += [g.interiorRing(i).points() for i in range(g.numInteriorRings())]
                polys.append(rings)
            return polys

        return super().nestedPointList(geom)

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
                v.extend(pt)

            f = []
            for c in tris.faces:
                f.extend(c)

        else:
            v = tris.vertices
            f = tris.faces

        d = {"triangles": {"v": v, "f": f}}
        if self.centroids:
            d["centroids"] = [[x, y, z if z == z else 0] for x, y, z in self.centroids]
        return d

    def toDict2(self, flat=False):
        tris = IndexedTriangles2D()
        for v0, v1, v2 in self.triangles:
            tris.addTriangle(v0, v1, v2)

        if flat:
            v = []
            for pt in tris.vertices:
                v.extend(pt)

            f = []
            for c in tris.faces:
                f.extend(c)

        else:
            v = tris.vertices
            f = tris.faces

        d = {"triangles": {"v": v, "f": f}}
        if self.centroids:
            d["centroids"] = [[x, y] for x, y, z in self.centroids]
        return d

    @classmethod
    def fromQgsGeometry(cls, geometry, z_func, transform_func, centroid=True, drop_z=False,
                        ccw2d=False, use_z_func_cache=False, use_earcut=False):
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
            pt = geometry.centroid().asPoint()
            if drop_z:
                c = transform_func(pt.x(), pt.y(), z_func(pt.x(), pt.y()))
            else:
                # use z coordinate of first vertex (until QgsAbstractGeometry supports z coordinate of centroid)
                try:
                    c = transform_func(pt.x(), pt.y(), g.vertexAt(QgsVertexId(0, 0, 0)).z() + z_func(pt.x(), pt.y()))
                except TypeError:   # if isinstance(g, QgsTriangle)
                    c = transform_func(pt.x(), pt.y(), g.vertexAt(0).z() + z_func(pt.x(), pt.y()))

            geom.centroids.append(c)

        # vertex transform function
        if drop_z:
            v_func = lambda x, y, z: transform_func(x, y, z_func(x, y))
        else:
            v_func = lambda x, y, z: transform_func(x, y, z + z_func(x, y))

        # triangulation
        if use_earcut:
            vertices = []
            for poly in cls.nestedPointList(g):
                if len(poly) == 1 and len(poly[0]) == 4:
                    vertices.extend([v_func(pt.x(), pt.y(), pt.z()) for pt in poly[0][0:3]])
                else:
                    bnds = [[[pt.x(), pt.y(), pt.z()] for pt in bnd] for bnd in poly]
                    data = earcut.flatten(bnds)
                    v = data["vertices"]
                    triangles = earcut.earcut(v, data["holes"], 3)
                    vertices.extend([v_func(v[3 * i], v[3 * i + 1], v[3 * i + 2]) for i in triangles])
        else:
            tes = QgsTessellator(0, 0, False)
            addPolygon = tes.addPolygon
            for poly in cls.singleGeometries(g):
                addPolygon(poly, 0)

            # mp = tes.asMultiPolygon()     # not available
            data = tes.data()       # [x0, z0, -y0, x1, z1, -y1, ...]
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
            area += (p[i][0] - p[i + 1][0]) * (p[i][1] + p[i + 1][1])
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
        if hasattr(linearRing[0], "x"):
            return GeometryUtils._signedAreaA(linearRing) < 0
        else:
            return GeometryUtils._signedArea(linearRing) < 0


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
        self.width, self.height = (extent.width(), extent.height())
        self.xmin, self.ymin = (center.x() - self.width / 2,
                                center.y() - self.height / 2)
        self.xmax, self.ymax = (center.x() + self.width / 2,
                                center.y() + self.height / 2)
        self.xres = self.width / x_segments
        self.yres = self.height / y_segments

        self.vbands = self.hbands = None

    def setupBands(self):
        xmin, ymin, xmax, ymax = (self.xmin, self.ymin, self.xmax, self.ymax)
        xres, yres = (self.xres, self.yres)

        vrects = []
        hrects = []
        vbands = []
        hbands = []

        for x in range(self.x_segments):
            f = QgsFeature(x)
            r = QgsRectangle(xmin + x * xres, ymin,
                             xmin + (x + 1) * xres, ymax)
            f.setGeometry(QgsGeometry.fromRect(r))
            vrects.append(r)
            vbands.append(f)

        for y in range(self.y_segments):
            f = QgsFeature(y)
            r = QgsRectangle(xmin, ymax - (y + 1) * yres,
                             xmax, ymax - y * yres)
            f.setGeometry(QgsGeometry.fromRect(r))
            hrects.append(r)
            hbands.append(f)

        self.vrects = vrects
        self.hrects = hrects
        self.vbands = vbands
        self.hbands = hbands

        self.vidx = QgsSpatialIndex()
        self.vidx.addFeatures(vbands)

        self.hidx = QgsSpatialIndex()
        self.hidx.addFeatures(hbands)

    def vSplit(self, geom):
        """split polygon vertically"""
        for idx in self.vidx.intersects(geom.boundingBox()):
            geometry = geom.clipped(self.vrects[idx])
            if geometry:
                yield idx, geometry

    def hSplit(self, geom):
        """split polygon horizontally"""
        for idx in self.hidx.intersects(geom.boundingBox()):
            geometry = geom.clipped(self.hrects[idx])
            if geometry:
                yield idx, geometry

    def splitPolygonXY(self, geom):
        return QgsGeometry.fromMultiPolygonXY(list(self._splitPolygon(geom)))

    def splitPolygon(self, geom):
        z_func = lambda x, y: self.valueOnSurface(x, y) or 0
        cache = FunctionCacheXY(z_func)
        z_func = cache.func

        polygons = QgsMultiPolygon()
        for poly in self._splitPolygon(geom):
            p = QgsPolygon()
            ring = QgsLineString()
            for pt in poly[0]:
                ring.addVertex(QgsPoint(pt.x(), pt.y(), z_func(pt.x(), pt.y())))
            p.setExteriorRing(ring)

            for bnd in poly[1:]:
                ring = QgsLineString()
                for pt in bnd:
                    ring.addVertex(QgsPoint(pt.x(), pt.y(), z_func(pt.x(), pt.y())))
                p.addInteriorRing(ring)
            polygons.addGeometry(p)
        return QgsGeometry(polygons)

    def _splitPolygon(self, geom):
        if self.vbands is None:
            self.setupBands()

        for x, vc in self.vSplit(geom):
            for y, c in self.hSplit(vc):
                if c.isEmpty():
                    continue

                for poly in PolygonGeometry.nestedPointXYList(c):
                    bnds = [[[pt.x(), pt.y()] for pt in bnd] for bnd in poly]
                    data = earcut.flatten(bnds)
                    v = data["vertices"]
                    triangles = earcut.earcut(v, data["holes"], data["dimensions"])
                    vertices = [QgsPointXY(v[2 * i], v[2 * i + 1]) for i in triangles]

                    for i in range(0, len(vertices), 3):
                        yield [vertices[i:i + 3]]

    def segmentizeBoundaries(self, geom):
        """geom: QgsGeometry (polygon or multi-polygon)"""

        xmin, ymax = (self.xmin, self.ymax)
        xres, yres = (self.xres, self.yres)
        z_func = self.valueOnSurface

        polys = []
        for polygon in PolygonGeometry.nestedPointXYList(geom):
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
        x = (x - self.xmin) / self.width
        y = (y - self.ymin) / self.height
        if x < 0 or 1 < x or y < 0 or 1 < y:
            return None

        mx = x * self.x_segments
        my = (1 - y) * self.y_segments     # inverted. top is 0.
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

        z0, z1 = (self.value(mx0, my0), self.value(mx0 + 1, my0))
        z2, z3 = (self.value(mx0, my0 + 1), self.value(mx0 + 1, my0 + 1))

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
        vi = self.vidx.get(v[1], self.EMPDICT).get(v[0])
        if vi is not None:
            return vi

        vi = len(self.vertices)
        self.vertices.append(v)

        self.vidx[v[1]] = self.vidx.get(v[1], {})
        self.vidx[v[1]][v[0]] = vi
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
        vi = self.vidx.get(v[2], self.EMPDICT).get(v[1], self.EMPDICT).get(v[0])
        if vi is not None:
            return vi

        vi = len(self.vertices)
        self.vertices.append(v)

        self.vidx[v[2]] = self.vidx.get(v[2], {})
        self.vidx[v[2]][v[1]] = self.vidx[v[2]].get(v[1], {})
        self.vidx[v[2]][v[1]][v[0]] = vi
        return vi


def dissolvePolygonsWithinExtent(polygon_layer, extent, crs):
    """dissolve polygons of the polygon_layer and clip the dissolution with the extent
       polygon_layer: QgsVectorLayer
       extent: MapExtent
       crs: QgsCoordinateReferenceSystem. CRS of the extent"""
    extGeom = extent.geometry()
    rotation = extent.rotation()
    transform = QgsCoordinateTransform(polygon_layer.crs(), crs, QgsProject.instance())

    combi = None
    request = QgsFeatureRequest()
    request.setFilterRect(transform.transformBoundingBox(extent.boundingBox(), QgsCoordinateTransform.ReverseTransform))
    for f in polygon_layer.getFeatures(request):
        geometry = f.geometry()
        if geometry is None:
            logMessage("Null geometry skipped")
            continue

        # transform geometry from the layer CRS to the project CRS
        geom = QgsGeometry(geometry)
        if geom.transform(transform) != 0:
            logMessage("Failed to transform geometry to project CRS", warning=True)
            continue

        # check if geometry intersects with the base extent
        if rotation and not extGeom.intersects(geom):
            continue

        if combi:
            combi = combi.combine(geom)
        else:
            combi = geom

    if combi is None:
        return None

    # clip geom with slightly smaller extent than the extent
    # to make sure that the clipped polygon is contained within the extent
    geom = combi.intersection(extent.clone().scale(0.9999).geometry())
    if geom is None:
        return None

    # check if geometry is empty
    if geom.isEmpty():
        logMessage("empty geometry")
        return None

    return geom
