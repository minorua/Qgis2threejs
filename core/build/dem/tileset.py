# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import json
import math

from qgis.core import QgsPoint

from ...mapextent import MapExtent
from ...boundingvolume import BoundingVolume


class Tileset:

    TILE_SEGMENTS = 128

    def __init__(self, jsLayerId, cols, rows, boundingVolume: BoundingVolume, localOrigin: QgsPoint):
        self.jsLayerId = jsLayerId
        self.cols = cols
        self.rows = rows
        self.boundingVolume = boundingVolume
        self.tile_cols = math.ceil((cols - 1) / self.TILE_SEGMENTS)
        self.tile_rows = math.ceil((rows - 1) / self.TILE_SEGMENTS)
        self.localOrigin = localOrigin

    def maxLevel(self):
        tile_count = max(self.tile_cols, self.tile_rows)
        return max(0, tile_count - 1).bit_length()

    def metadata(self, asJson=False):
        width, height = self.boundingVolume.xSize(), self.boundingVolume.ySize()
        root_error = max(width, height) / self.TILE_SEGMENTS * 0.5
        max_level = self.maxLevel()

        x0, y0, z0 = self.localOrigin.x(), self.localOrigin.y(), self.localOrigin.z()

        def tile_node(level, x, y):
            tile_scale = 1 / (1 << level)
            xmin = self.boundingVolume.xmin + width * x * tile_scale - x0
            ymin = self.boundingVolume.ymin + height * y * tile_scale - y0
            xmax = xmin + width * tile_scale
            ymax = ymin + height * tile_scale
            zmin = self.boundingVolume.zmin - z0
            zmax = self.boundingVolume.zmax - z0

            node = {
                "boundingVolume": {
                    "box": BoundingVolume(xmin, ymin, zmin,
                                          xmax, ymax, zmax).toObbData()
                },
                "geometricError": root_error * tile_scale,
                "refine": "REPLACE",
                "content": {
                    "uri": f"~dem/{self.jsLayerId}/{level}/{x}/{y}.tile"
                }
            }

            if level < max_level:
                next_level = level + 1
                children = []
                for cy in range(y * 2, min(y * 2 + 2, self.tile_rows)):
                    for cx in range(x * 2, min(x * 2 + 2, self.tile_cols)):
                        children.append(tile_node(next_level, cx, cy))

                if children:
                    node["children"] = children

            return node

        d = {
            "asset": {
                "version": "1.0"
            },
            "geometricError": root_error,
            "root": tile_node(0, 0, 0)
        }

        return json.dumps(d, ensure_ascii=True, indent=2) if asJson else d      # ensure_ascii=True

    def build(self):
        return {
            "type": "layer",
            "id": self.jsLayerId,
            "tileset": self.metadata()
        }

    def tileExtent(self, level, x, y):
        width = self.boundingVolume.xSize()
        height = self.boundingVolume.ySize()
        tile_scale = 1 / (1 << level)  # 2^(-level)

        xmin = self.boundingVolume.xmin + width * x * tile_scale
        ymin = self.boundingVolume.ymin + height * y * tile_scale
        xmax = xmin + width * tile_scale
        ymax = ymin + height * tile_scale

        tile_width = xmax - xmin
        tile_height = ymax - ymin
        center = QgsPoint((xmin + xmax) / 2, (ymin + ymax) / 2)

        return MapExtent(center, tile_width, tile_height)
