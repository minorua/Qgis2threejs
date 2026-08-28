# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from .mapextent import MapExtent


class BoundingVolume:

    def __init__(self, xmin, ymin, zmin, xmax, ymax, zmax):
        self.xmin = xmin
        self.ymin = ymin
        self.zmin = zmin
        self.xmax = xmax
        self.ymax = ymax
        self.zmax = zmax

    def xSize(self):
        return self.xmax - self.xmin

    def ySize(self):
        return self.ymax - self.ymin

    def zSize(self):
        return self.zmax - self.zmin

    def toObbData(self):
        hx = self.xSize() / 2
        hy = self.ySize() / 2
        hz = self.zSize() / 2

        cx = self.xmin + hx
        cy = self.ymin + hy
        cz = self.zmin + hz

        return [
            cx, cy, cz,
            hx, 0, 0,
            0, hy, 0,
            0, 0, hz
        ]

    @classmethod
    def fromExtent(cls, extent: MapExtent, zmin, zmax):
        rect = extent.unrotatedRect()
        return cls(rect.xMinimum(), rect.yMinimum(), zmin, rect.xMaximum(), rect.yMaximum(), zmax)
