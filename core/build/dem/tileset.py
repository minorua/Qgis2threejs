# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass
import math

from qgis.core import QgsPoint, QgsRectangle

from ...mapextent import GridShape, RegularGrid, ZRange

TILE_SEGMENTS = 128


@dataclass
class Tile:
    level: int
    x: int
    y: int
    rect: QgsRectangle


class Tileset:

    def __init__(self, jsLayerId, grid: RegularGrid, zrange: ZRange, localOrigin: QgsPoint, tileSegments=TILE_SEGMENTS):
        self.jsLayerId = jsLayerId
        self.grid = grid
        self.zrange = zrange
        self.localOrigin = localOrigin
        self.tileSegments = tileSegments

        self.boundingRect = grid.rect
        self.gridResolution = grid.xres()

        cols = math.ceil((grid.shape.cols - 1) / self.tileSegments)
        rows = math.ceil((grid.shape.rows - 1) / self.tileSegments)
        self.tileShape = GridShape(cols, rows)
        self.maxLevel = max(0, max(cols, rows) - 1).bit_length()

    def tilesetParams(self):
        """
        @returns {TilesetParams}
        """
        origin_x = self.localOrigin.x()
        origin_y = self.localOrigin.y()
        origin_z = self.localOrigin.z()

        xmin = self.boundingRect.xMinimum() - origin_x
        xmax = self.boundingRect.xMaximum() - origin_x
        ymin = self.boundingRect.yMinimum() - origin_y
        ymax = self.boundingRect.yMaximum() - origin_y
        zmin = self.zrange.zmin - origin_z
        zmax = self.zrange.zmax - origin_z

        return {
            "boundingBox": {
                "min": [xmin, ymin, zmin],
                "max": [xmax, ymax, zmax]
            },
            "gridResolution": self.gridResolution,
            "gridCols": self.grid.shape.cols,
            "gridRows": self.grid.shape.rows,
            "maxLevel": self.maxLevel,
            "tileSegments": self.tileSegments
        }

    def _tileRect(self, level, x, y):
        level_scale = 1 << (self.maxLevel - level)
        tile_size = self.gridResolution * self.tileSegments * level_scale

        tile_xmin = self.boundingRect.xMinimum() + tile_size * x
        tile_ymin = self.boundingRect.yMinimum() + tile_size * y
        tile_xmax = tile_xmin + tile_size
        tile_ymax = tile_ymin + tile_size

        return tile_xmin, tile_ymin, tile_xmax, tile_ymax

    def tileRect(self, level, x, y):
        return QgsRectangle(*self._tileRect(level, x, y))

    def iterTiles(self, minLevel=None, maxLevel=None):
        if minLevel is None:
            minLevel = self.maxLevel

        if maxLevel is None:
            maxLevel = self.maxLevel

        max_level_tile_size = self.gridResolution * self.tileSegments

        for level in range(minLevel, maxLevel + 1):
            level_scale = 1 << (self.maxLevel - level)
            tile_size = max_level_tile_size * level_scale

            cols = math.ceil(self.boundingRect.width() / tile_size)
            rows = math.ceil(self.boundingRect.height() / tile_size)

            for row in range(rows):
                for col in range(cols):
                    yield Tile(level, col, row, self.tileRect(level, col, row))
