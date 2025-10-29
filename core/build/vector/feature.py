# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from .object import ObjectType
from ...const import LayerType, PropertyID as PID
from ...geometry import VectorGeometry, PointGeometry, LineGeometry, PolygonGeometry, TINGeometry


LayerType2GeomClass = {
    LayerType.POINT: PointGeometry,
    LayerType.LINESTRING: LineGeometry,
    LayerType.POLYGON: PolygonGeometry
}


class Feature:
    """Represents a feature with 3D geometry. Generated from a QgsFeature and passed to the builder."""

    def __init__(self, vlayer, geom, props, attrs=None):

        self.layerType = vlayer.type
        self.ot = vlayer.ot

        self.geom = geom            # an instance of QgsGeometry
        self.props = props          # a dict
        self.attributes = attrs     # a list or None

        self.material = self.model = None

    def clipGeometry(self, extent):
        r = extent.rotation()
        if r:
            self.geom.rotate(r, extent.center())

        self.geom = self.geom.clipped(extent.unrotatedRect())
        if r:
            self.geom.rotate(-r, extent.center())

        return self.geom

    def geometry(self, z_func, mapTo3d, useZM=VectorGeometry.NotUseZM, baseExtent=None, grid=None):
        alt = self.prop(PID.ALT, 0)
        zf = lambda x, y: z_func(x, y) + alt

        transform_func = mapTo3d.transform

        if self.layerType != LayerType.POLYGON:
            return LayerType2GeomClass[self.layerType].fromQgsGeometry(self.geom, zf, transform_func, useZM=useZM)

        objType = type(self.ot)
        if objType == ObjectType.Polygon:
            return TINGeometry.fromQgsGeometry(self.geom, zf, transform_func,
                                               drop_z=(useZM == VectorGeometry.NotUseZM))

        if objType == ObjectType.Extruded:
            return PolygonGeometry.fromQgsGeometry(self.geom, zf, transform_func,
                                                   useCentroidHeight=True,
                                                   centroidPerPolygon=True)

        # Overlay
        border = bool(self.prop(PID.C2) is not None)
        if grid is None:
            # absolute z coordinate
            g = TINGeometry.fromQgsGeometry(self.geom, zf, transform_func, drop_z=True)
            if border:
                g.bnds_list = PolygonGeometry.fromQgsGeometry(self.geom, zf, transform_func).toLineGeometryList()
            return g

        # relative to DEM
        transform_func = mapTo3d.transform

        if baseExtent.rotation():
            self.geom.rotate(baseExtent.rotation(), baseExtent.center())

        polys = grid.splitPolygon(self.geom)
        g = TINGeometry.fromQgsGeometry(polys, zf, transform_func, use_earcut=True)

        if border:
            bnds = grid.segmentizeBoundaries(self.geom)
            g.bnds_list = [LineGeometry.fromQgsGeometry(bnd, zf, transform_func, useZM=VectorGeometry.UseZ) for bnd in bnds]
        return g

    def prop(self, pid, def_val=None):
        return self.props.get(pid, def_val)

    def hasProp(self, pid):
        return pid in self.props
