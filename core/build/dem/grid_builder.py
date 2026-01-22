# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import base64
import json
import struct
from qgis.PyQt.QtCore import QByteArray
from qgis.core import QgsGeometry, QgsPointXY

from .property_reader import DEMPropertyReader
from ...geometry import VectorGeometry, LineGeometry, TINGeometry
from ...mapextent import MapExtent
from ....conf import DEBUG_MODE, DEF_SETS
from ....utils import hex_color, logger, parseFloat


class DEMGridBuilder:
    """Generates 3D geometry grids based on DEM data."""

    def __init__(self, layer, settings, provider, mtlManager, pathRoot=None, urlRoot=None):
        self.layer = layer
        self.properties = layer.properties

        self.settings = settings
        self.provider = provider
        self.mtlManager = mtlManager

        self.pathRoot = pathRoot
        self.urlRoot = urlRoot

    def setup(self, blockIndex, grid_seg, extent, planeWidth, planeHeight, offsetX=0, offsetY=0, roughness=1, edgeRoughness=1, clip_geometry=None, neighbors=None):
        self.blockIndex = blockIndex
        self.grid_seg = grid_seg
        self.extent = extent
        self.planeWidth = planeWidth
        self.planeHeight = planeHeight
        self.offsetX = offsetX
        self.offsetY = offsetY
        self.roughness = roughness
        self.edgeRoughness = edgeRoughness
        self.clip_geometry = clip_geometry
        self.neighbors = neighbors or []

        self.edges = None

    def build(self):
        b = {
            "type": "block",
            "layer": self.layer.jsLayerId,
            "block": self.blockIndex,
            "width": self.planeWidth,
            "height": self.planeHeight,
            "translate": [self.offsetX, self.offsetY, 0],
            "zScale": self.settings.mapTo3d().zScale
        }

        if self.clip_geometry:
            geom = self.clipped(self.clip_geometry)

            if self.settings.localMode or self.settings.isPreview:
                b["geom"] = geom
            else:
                tail = f"{self.blockIndex}.json"

                with open(self.pathRoot + tail, "w", encoding="utf-8") as f:
                    json.dump(geom, f, ensure_ascii=False, indent=2 if DEBUG_MODE else None)

                b["geom"] = {"url": self.urlRoot + tail}
        else:
            columns, rows = (self.grid_seg.width() + 1, self.grid_seg.height() + 1)

            if self.edgeRoughness == 1 and len(self.neighbors) == 0:
                ba = self.provider.read(columns, rows, self.extent)
            else:
                grid_values = list(self.provider.readValues(columns, rows, self.extent))
                self.processEdges(grid_values, self.edgeRoughness)
                ba = struct.pack(f"{columns * rows}f", *grid_values)

            b["grid"] = self._gridData(columns, rows, ba)

        # TODO: move to layer property
        opacity = DEMPropertyReader.opacity(self.properties)

        # sides and bottom
        if self.properties.get("checkBox_Sides"):
            mi = self.mtlManager.getMeshMaterialIndex(hex_color(self.properties.get("colorButton_Side", DEF_SETS.SIDE_COLOR), prefix="0x"), opacity)
            b["sides"] = {"mtl": self.mtlManager.build(mi),
                          "bottom": parseFloat(self.properties.get("lineEdit_Bottom"), DEF_SETS.Z_BOTTOM)}

        # edges
        if self.properties.get("checkBox_Frame") and not self.properties.get("radioButton_ClipPolygon"):
            mi = self.mtlManager.getLineIndex(hex_color(self.properties.get("colorButton_Edge", DEF_SETS.EDGE_COLOR), prefix="0x"), opacity)
            b["edges"] = {"mtl": self.mtlManager.build(mi)}

        # wireframe
        if self.properties.get("checkBox_Wireframe"):
            mi = self.mtlManager.getLineIndex(hex_color(self.properties.get("colorButton_Wireframe", DEF_SETS.WIREFRAME_COLOR), prefix="0x"), opacity)
            b["wireframe"] = {"mtl": self.mtlManager.build(mi)}

        return b

    def _gridData(self, columns, rows, bytearray):
        g = {
            "width": columns,
            "height": rows
        }

        if self.settings.requiresJsonSerializable:
            g["base64"] = base64.b64encode(bytearray).decode("ascii")
        elif self.settings.isPreview:       # for WebKit preview
            g["binary"] = QByteArray(bytearray)
        else:
            # write grid values to an binary file
            tail = f"{self.blockIndex}.bin"
            g["url"] = self.urlRoot + tail

            with open(self.pathRoot + tail, "wb") as f:
                f.write(bytearray)

        return g

    def clipped(self, clip_geometry):
        transform_func = self.settings.mapTo3d().transformXY

        # create a grid geometry and split polygons with the grid
        grid = self.provider.readAsGridGeometry(self.grid_seg.width() + 1, self.grid_seg.height() + 1, self.extent)

        if self.extent.rotation():
            clip_geometry = QgsGeometry(clip_geometry)
            clip_geometry.rotate(self.extent.rotation(), self.extent.center())

        bnds = grid.segmentizeBoundaries(clip_geometry)
        polys = grid.splitPolygon(clip_geometry)

        tin = TINGeometry.fromQgsGeometry(polys, None, transform_func, centroid=False, use_earcut=True)
        d = tin.toDict(flat=True)

        polygons = []
        for bnd in bnds:
            geom = LineGeometry.fromQgsGeometry(bnd, None, transform_func, useZM=VectorGeometry.UseZ)
            polygons.append(geom.toList(flat=True))
        d["polygons"] = polygons
        return d

    def processEdges(self, grid_values, roughness):

        if self.offsetX == 0 and self.offsetY == 0:
            self.processEdgesCenter(grid_values, roughness)
            return

        grid_width, grid_height = (self.grid_seg.width() + 1,
                                   self.grid_seg.height() + 1)

        for sx, sy, neighbor, roughness in self.neighbors:
            if self.roughness <= roughness:
                continue
            if neighbor.edges is None:
                logger.warning("Neighbor block {} holds no edge values.".format(neighbor.blockIndex))
                continue

            if (sx, sy) == (0, -1):
                # top edge
                for x in range(grid_width):
                    grid_values[x] = neighbor.edges[0][x]

            elif (sx, sy) == (0, 1):
                # bottom edge
                offset = grid_width * (grid_height - 1)
                for x in range(grid_width):
                    grid_values[offset + x] = neighbor.edges[3][x]

            elif (sx, sy) == (-1, 0):
                # right edge
                offset = grid_width - 1
                for y in range(grid_height):
                    grid_values[offset + grid_width * y] = neighbor.edges[1][y]

            elif (sx, sy) == (1, 0):
                # left edge
                for y in range(grid_height):
                    grid_values[grid_width * y] = neighbor.edges[2][y]

            elif (sx, sy) == (-1, -1):
                # top-right corner
                grid_values[grid_width - 1] = neighbor.edges[0][0]

            elif (sx, sy) == (1, -1):
                # top-left corner
                grid_values[0] = neighbor.edges[0][grid_width - 1]

            elif (sx, sy) == (-1, 1):
                # bottom-right corner
                grid_values[grid_width * grid_height - 1] = neighbor.edges[3][0]

            elif (sx, sy) == (1, 1):
                # bottom-left corner
                grid_values[grid_width * (grid_height - 1)] = neighbor.edges[3][grid_width - 1]

            else:
                logger.warning("Edge processing: invalid sx and sy ({}, {})".format(sx, sy))

    def processEdgesCenter(self, grid_values, roughness):

        grid_width, grid_height = (self.grid_seg.width() + 1,
                                   self.grid_seg.height() + 1)
        rg_grid_width, rg_grid_height = (self.grid_seg.width() // roughness + 1,
                                         self.grid_seg.height() // roughness + 1)
        ii = range(roughness)[1:]

        iy0 = grid_width * (grid_height - 1)
        e_top = [grid_values[0]]
        e_bottom = [grid_values[iy0]]

        for x0 in range(rg_grid_width - 1):
            # top edge
            ix0 = x0 * roughness
            z0 = grid_values[ix0]
            z1 = grid_values[ix0 + roughness]
            s = (z1 - z0) / roughness
            for i in ii:
                grid_values[ix0 + i] = z0 + s * i

            e_top.append(z1)

            # bottom edge
            z0 = grid_values[iy0 + ix0]
            z1 = grid_values[iy0 + ix0 + roughness]
            s = (z1 - z0) / roughness
            for i in ii:
                grid_values[iy0 + ix0 + i] = z0 + s * i

            e_bottom.append(z1)

        e_left = [grid_values[0]]
        e_right = [grid_values[grid_width - 1]]

        rw = roughness * grid_width
        for y0 in range(rg_grid_height - 1):
            # left edge
            iy0 = y0 * rw
            z0 = grid_values[iy0]
            z1 = grid_values[iy0 + rw]
            s = (z1 - z0) / roughness
            for i in ii:
                grid_values[iy0 + i * grid_width] = z0 + s * i

            e_left.append(z1)

            # right edge
            iy0 += grid_width - 1
            z0 = grid_values[iy0]
            z1 = grid_values[iy0 + rw]
            s = (z1 - z0) / roughness
            for i in ii:
                grid_values[iy0 + i * grid_width] = z0 + s * i

            e_right.append(z1)

        self.edges = [e_bottom, e_left, e_right, e_top]

    def getValue(self, x, y):

        def _getValue(gx, gy):
            return self.grid_values[gx + self.grid_width * gy]

        if 0 <= x and x <= self.grid_width - 1 and 0 <= y and y <= self.grid_height - 1:
            ix, iy = int(x), int(y)
            sx, sy = x - ix, y - iy

            z11 = _getValue(ix, iy)
            z21 = 0 if x == self.grid_width - 1 else _getValue(ix + 1, iy)
            z12 = 0 if y == self.grid_height - 1 else _getValue(ix, iy + 1)
            z22 = 0 if x == self.grid_width - 1 or y == self.grid_height - 1 else _getValue(ix + 1, iy + 1)

            return (1 - sx) * ((1 - sy) * z11 + sy * z12) + sx * ((1 - sy) * z21 + sy * z22)    # bilinear interpolation

        return 0    # as safe null value


class DEMTileGridBuilder(DEMGridBuilder):

    def setup(self, blockIndex, segments, tileExtent, offsetX, offsetY, layerExtent, clip_geometry=None):
        self.blockIndex = blockIndex
        self.segments = segments
        self.tileExtent = tileExtent
        self.tileSize = tileExtent.width()
        self.offsetX = offsetX
        self.offsetY = offsetY
        self.layerExtent = layerExtent
        self.clip_geometry = clip_geometry

    def build(self):
        b = {
            "type": "block",
            "layer": self.layer.jsLayerId,
            "block": self.blockIndex,
            "segments": self.segments,
            "tileSize": self.tileSize,
            "translate": [self.offsetX, self.offsetY, 0],
            "zScale": self.settings.mapTo3d().zScale,
        }

        if self.clip_geometry:
            # TODO: implement clipped tile
            pass

        else:
            segment_size = self.tileSize / self.segments
            half_segment_size = segment_size / 2

            ulx, uly = self.tileExtent.point(0, 1)              # A' (px is pt)
            tile_lrx, tile_lry = self.tileExtent.point(1, 0)    # B' (px is pt)

            _lrx, _lry = self.layerExtent.point(1, 0)           # C  (px is area)
            layer_lrx, layer_lry = _lrx - half_segment_size, _lry + half_segment_size # C' (px is pt)

            lrx, lry = min(layer_lrx, tile_lrx), max(layer_lry, tile_lry)

            valid_width = lrx - ulx
            valid_height = uly - lry
            center = QgsPointXY(ulx + valid_width / 2, uly - valid_height / 2)

            valid_extent = MapExtent(center, valid_width, valid_height)   # extent in the tile that contains actual data

            columns = int(valid_width / segment_size + 1)
            rows = int(valid_height / segment_size + 1)
            ba = self.provider.read(columns, rows, valid_extent)

            b["grid"] = self._gridData(columns, rows, ba)

        # TODO:
        # sides, bottom, edges and wireframe

        return b
