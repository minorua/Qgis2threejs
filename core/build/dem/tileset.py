# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass
import json
import math

from qgis.core import QgsPoint, QgsRectangle

from ...mapextent import BoundingVolume, GridShape, RegularGrid, ZRange

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

    def metadata(self, asJson=False):
        max_level_tile_size = self.gridResolution * self.tileSegments
        max_level_error = self.gridResolution * 0.5

        origin_x = self.localOrigin.x()
        origin_y = self.localOrigin.y()
        origin_z = self.localOrigin.z()

        xmin = self.boundingRect.xMinimum() - origin_x
        ymin = self.boundingRect.yMinimum() - origin_y
        zmin = self.zrange.zmin - origin_z
        zmax = self.zrange.zmax - origin_z

        def tile_node(level, x, y):
            level_scale = 1 << (self.maxLevel - level)
            tile_size = max_level_tile_size * level_scale
            geometric_error = max_level_error * level_scale

            tile_xmin_rel = tile_size * x
            tile_ymin_rel = tile_size * y
            if tile_xmin_rel >= self.boundingRect.width() or tile_ymin_rel >= self.boundingRect.height():
                return None

            tile_xmin = xmin + tile_xmin_rel
            tile_ymin = ymin + tile_ymin_rel
            tile_xmax = tile_xmin + tile_size
            tile_ymax = tile_ymin + tile_size

            node = {
                "boundingVolume": {
                    "box": BoundingVolume(tile_xmin, tile_ymin, zmin,
                                          tile_xmax, tile_ymax, zmax).toObbData()
                },
                "geometricError": geometric_error,
                "refine": "REPLACE",
                "content": {
                    "uri": f"dem/{self.jsLayerId}/{level}/{x}/{y}.tile"
                }
            }

            if level < self.maxLevel:
                child_level = level + 1
                children = []
                for cy in range(y * 2, min(y * 2 + 2, self.tileShape.rows)):
                    for cx in range(x * 2, min(x * 2 + 2, self.tileShape.cols)):
                        child_node = tile_node(child_level, cx, cy)
                        if child_node:
                            children.append(child_node)

                if children:
                    node["children"] = children

            return node

        root_geometric_error = max_level_error * (1 << self.maxLevel)
        d = {
            "asset": {
                "version": "1.0"
            },
            "geometricError": root_geometric_error,
            "root": tile_node(0, 0, 0)
        }

        return json.dumps(d, ensure_ascii=True, indent=2) if asJson else d

    def build(self):
        return {
            "type": "layer",
            "id": self.jsLayerId,
            "tileset": self.metadata()
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
