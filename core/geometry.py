# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from math import ceil, floor
from qgis.core import (
    Qgis, QgsGeometry, QgsPointXY, QgsRectangle, QgsCoordinateTransform, QgsFeatureRequest,
    QgsPoint, QgsMultiPoint, QgsLineString, QgsMultiLineString, QgsPolygon, QgsMultiPolygon, QgsGeometryCollection,
    QgsProject, QgsTessellator, QgsVertexId, QgsWkbTypes
)

from .geom_types import Face, Vector3, TransformFunc, Triangle, ZFunc
from ..utils.logging import logger


class VectorGeometry:

    NotUseZM = 0
    UseZ = 1
    UseM = 2

    @classmethod
    def nestedPointXYList(cls, geom):
        if geom.wkbType() == Qgis.WkbType.GeometryCollection:
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

        logger.warning("{}: {} type is not supported yet.".format(cls.__name__, type(geom).__name__))
        return []

    @classmethod
    def singleGeometries(cls, geom):
        """geom: a subclass object of QgsAbstractGeometry"""
        if isinstance(geom, QgsGeometryCollection):
            g = []
            for i in range(geom.numGeometries()):
                g.extend(cls.singleGeometries(geom.geometryN(i)))
            return g

        logger.warning("{}: {} type is not supported yet.".format(cls.__name__, type(geom).__name__))
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
        if QgsWkbTypes.singleType(QgsWkbTypes.flatType(geom.wkbType())) == Qgis.WkbType.Point:
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
        if QgsWkbTypes.singleType(QgsWkbTypes.flatType(geom.wkbType())) == Qgis.WkbType.LineString:
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
        if QgsWkbTypes.singleType(QgsWkbTypes.flatType(geom.wkbType())) == Qgis.WkbType.Polygon:
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
        self.triangles: list[Triangle] = []
        self.centroids: list[Vector3] = []

    def toDict(self, flat=True):
        """
        @returns {MeshData} if flat is True
        """
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

        d = {
            "vertices": v,
            "indices": f
        }

        if self.centroids:
            d["centroids"] = [[x, y, z if z == z else 0] for x, y, z in self.centroids]
        return d

    @classmethod
    def fromQgsGeometry(cls, geometry, z_func: ZFunc, transform_func: TransformFunc, centroid=True, drop_z=False,
                        ccw2d=False, use_z_func_cache=False):
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
        tes = QgsTessellator()
        tes.setTriangulationAlgorithm(Qgis.TriangulationAlgorithm.Earcut)

        for poly in cls.singleGeometries(g):
            tes.addPolygon(poly, 0)

        fv = memoryview(tes.vertexBuffer()).cast("f")    # [x0, z0, -y0, ...]
        floats_per_vertex = tes.stride() // 4            # stride = n * sizeof( float )

        verts = [
            v_func(fv[i], -fv[i + 2], fv[i + 1])
            for i in range(0, len(fv), floats_per_vertex)
        ]

        indices = memoryview(tes.indexBuffer()).cast("I")

        tris = []
        if ccw2d:
            # orient triangles to counter-clockwise order
            is_clockwise = GeometryUtils.isClockwise

            for i in range(0, len(indices), 3):
                v0 = verts[indices[i]]
                v1 = verts[indices[i + 1]]
                v2 = verts[indices[i + 2]]

                if is_clockwise([v0, v1, v2, v0]):
                    tris.append((v0, v2, v1))
                else:
                    tris.append((v0, v1, v2))
        else:
            # use original vertex order
            tris = [
                (
                    verts[indices[i]],
                    verts[indices[i + 1]],
                    verts[indices[i + 2]]
                )
                for i in range(0, len(indices), 3)
            ]

        geom.triangles = tris

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
    Geometry of a regular grid with DEM values,
    used to generate and clip terrain triangles.
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

    def _vRect(self, x):
        """rectangle of vertical band x (full height, one column wide)"""
        return QgsRectangle(self.xmin + x * self.xres, self.ymin,
                            self.xmin + (x + 1) * self.xres, self.ymax)

    def _hRect(self, y):
        """rectangle of horizontal band y (full width, one row tall)"""
        return QgsRectangle(self.xmin, self.ymax - (y + 1) * self.yres,
                            self.xmax, self.ymax - y * self.yres)

    def _xRange(self, bbox: QgsRectangle):
        """column indices that may intersect bbox"""
        c0 = max(floor((bbox.xMinimum() - self.xmin) / self.xres), 0)
        c1 = min(floor((bbox.xMaximum() - self.xmin) / self.xres), self.x_segments - 1)
        return range(c0, c1 + 1)

    def _yRange(self, bbox: QgsRectangle):
        """row indices that may intersect bbox"""
        r0 = max(floor((self.ymax - bbox.yMaximum()) / self.yres), 0)
        r1 = min(floor((self.ymax - bbox.yMinimum()) / self.yres), self.y_segments - 1)
        return range(r0, r1 + 1)

    def _vSplit(self, geom):
        """split polygon vertically"""
        for x in self._xRange(geom.boundingBox()):
            geometry = geom.clipped(self._vRect(x))
            if geometry and not geometry.isEmpty():
                yield x, geometry

    def _hSplit(self, geom):
        """split polygon horizontally"""
        for y in self._yRange(geom.boundingBox()):
            geometry = geom.clipped(self._hRect(y))
            if geometry and not geometry.isEmpty():
                yield y, geometry

    def _cellTriangles(self, x, y):
        xres, yres = (self.xres, self.yres)
        x0 = self.xmin + x * xres
        y0 = self.ymax - y * yres

        a = QgsPointXY(x0, y0)
        b = QgsPointXY(x0, y0 - yres)
        c = QgsPointXY(x0 + xres, y0 - yres)
        d = QgsPointXY(x0 + xres, y0)

        return [
            QgsGeometry.fromPolygonXY([[a, b, d, a]]),
            QgsGeometry.fromPolygonXY([[b, c, d, b]])
        ]

    def splitPolygon(self, geom) -> QgsGeometry:
        cellArea = self.xres * self.yres
        tolerance = cellArea * 1e-9

        geoms = []
        for x, vc in self._vSplit(geom):
            for y, c in self._hSplit(vc):
                if abs(c.area() - cellArea) < tolerance:
                    geoms.extend(self._cellTriangles(x, y))
                    continue

                for tri in self._cellTriangles(x, y):
                    part = tri.intersection(c)
                    if part and not part.isEmpty():
                        geoms.append(part)

        return QgsGeometry.collectGeometry(geoms)

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


class IndexedTriangles3D:

    def __init__(self):
        self.vertices: list[Vector3] = []
        self.faces: list[Face] = []
        self.vidx: dict[Vector3, int] = {}

    def addTriangle(self, v1: Vector3, v2: Vector3, v3: Vector3):
        vi1 = self._vertexIndex(v1)
        vi2 = self._vertexIndex(v2)
        vi3 = self._vertexIndex(v3)
        self.faces.append([vi1, vi2, vi3])

    def _vertexIndex(self, v: Vector3) -> int:
        vi = self.vidx.get(v)
        if vi is not None:
            return vi

        vi = len(self.vertices)
        self.vertices.append(v)

        self.vidx[v] = vi
        return vi


def dissolvePolygonsWithinExtent(polygon_layer, extent, crs):
    """dissolve polygons of the polygon_layer and clip the dissolution with the extent
       polygon_layer: QgsVectorLayer
       extent: MapExtent
       crs: QgsCoordinateReferenceSystem. CRS of the extent"""
    transform = QgsCoordinateTransform(polygon_layer.crs(), crs, QgsProject.instance())

    combi = None
    request = QgsFeatureRequest()
    request.setFilterRect(transform.transformBoundingBox(extent.boundingBox(), QgsCoordinateTransform.TransformDirection.Reverse))
    for f in polygon_layer.getFeatures(request):
        geometry = f.geometry()
        if geometry is None:
            logger.info("Null geometry skipped")
            continue

        # transform geometry from the layer CRS to the project CRS
        geom = QgsGeometry(geometry)
        if geom.transform(transform) != 0:
            logger.warning("Failed to transform geometry to project CRS")
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
        logger.info("empty geometry")
        return None

    return geom
