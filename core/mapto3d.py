# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.core import QgsPoint

from .geom_types import Vector3
from .mapextent import MapExtent


class MapTo3D:

    def __init__(self, mapExtent: MapExtent, origin: QgsPoint, zScale=1):
        # map
        self.mapExtent = mapExtent

        rect = mapExtent.unrotatedRect()
        self._xmin, self._ymin = (rect.xMinimum(), rect.yMinimum())
        self._width, self._height = (rect.width(), rect.height())

        # 3d
        self.origin = origin            # 3D world origin in map coordinates
        self.zScale = zScale

        self._originX, self._originY, self._originZ = (origin.x(), origin.y(), origin.z())

    def transform(self, x, y, z=0) -> Vector3:
        return (
            x - self._originX,
            y - self._originY,
            (z - self._originZ) * self.zScale
        )

    def transformXY(self, x, y, z=0) -> Vector3:
        return (
            x - self._originX,
            y - self._originY,
            z
        )

    def __repr__(self):
        origin = "({}, {}, {})".format(self.origin.x(), self.origin.y(), self.origin.z())
        return "MapTo3D(extent:{}, origin:{}, zScale:{})".format(str(self.mapExtent), origin, self.zScale)
