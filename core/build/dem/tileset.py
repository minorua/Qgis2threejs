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
        self.maxLevelTileShape = GridShape(cols, rows)
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

        for level in range(minLevel, maxLevel + 1):
            level_scale = 1 << (self.maxLevel - level)      # tile res. / grid res.
            tile_resolution = self.gridResolution * level_scale
            tile_size = tile_resolution * self.tileSegments

            tile_cols = math.floor(self.boundingRect.width() / tile_size)
            tile_rows = math.floor(self.boundingRect.height() / tile_size)

            rem_width = self.boundingRect.width() - tile_cols * tile_size
            rem_height = self.boundingRect.height() - tile_rows * tile_size

            rem_cols = round(rem_width / self.gridResolution)
            rem_rows = round(rem_height / self.gridResolution)

            if rem_cols >= level_scale:
                tile_cols += 1
            elif rem_cols:
                # TODO: extend tileRect here?
                pass


            if rem_rows >= level_scale:
                tile_rows += 1

            for row in range(tile_rows):
                for col in range(tile_cols):
                    yield Tile(level, col, row, self.tileRect(level, col, row))     # TODO: extend tileRect here?
