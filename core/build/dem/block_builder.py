# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import base64
import numpy as np
import struct

from qgis.PyQt.QtCore import QSize
from qgis.core import QgsGeometry, QgsPoint, QgsPointXY

from ...exportsettings import ExportSettings
from ...geometry import TINGeometry
from ...mapextent import MapExtent
from ....utils.js import writeBinaryContainer
from ....utils.logging import logger


class DEMBlockBuilderBase:

    def __init__(self, layer, settings: ExportSettings, provider, mtlManager, pathRoot=None, urlRoot=None):
        self.layer = layer
        self.properties = layer.properties

        self.settings = settings
        self.provider = provider
        self.mtlManager = mtlManager

        self.pathRoot = pathRoot
        self.urlRoot = urlRoot

    def setup(self, blockIndex, extent: MapExtent, localOrigin: QgsPoint):
        self.blockIndex = blockIndex
        self.extent = extent
        self.localOrigin = localOrigin

    def buildGridData(self, z_arr, extent: MapExtent, localOrigin: QgsPoint, nodata=None):
        """
        @returns {DEMGridData | DEMGridDataRef}
        """
        rows, cols = z_arr.shape
        bytearray = z_arr.astype(np.float32, copy=False).tobytes()

        g = {
            "columns": cols,
            "rows": rows
        }

        if nodata is not None:
            g["nodata"] = base64.b64encode(struct.pack("f", nodata)).decode("ascii")

        if self.settings.isPreview:
            g["base64"] = base64.b64encode(bytearray).decode("ascii")

        else:
            # write DEM values to a binary file
            tail = f"{self.blockIndex}.bin"

            g["url"] = self.urlRoot + tail

            with open(self.pathRoot + tail, "wb") as f:
                f.write(bytearray)

        return g

    def buildMeshData(self, z_arr, extent: MapExtent, localOrigin: QgsPoint, nodata=None, full_extent: MapExtent=None):
        """
        center: Coordinates of the origin

        @returns {DEMMeshData | DEMMeshDataRef}
        """
        if full_extent is None:
            full_extent = extent

        rows, cols = z_arr.shape

        c, r = np.meshgrid(np.arange(cols), np.arange(rows))

        gt = extent.geotransform(cols, rows)

        # Coordinates of the upper-left corner of the extent relative to the center
        x0 = gt[0] + 0.5 * (gt[1] + gt[2]) - localOrigin.x()
        y0 = gt[3] + 0.5 * (gt[4] + gt[5]) - localOrigin.y()

        # Coordinates
        x = x0 + c * gt[1] + r * gt[2]
        y = y0 + c * gt[4] + r * gt[5]
        z = z_arr - localOrigin.z() if localOrigin.z() else z_arr

        # UVs
        u = c / ((cols - 1) * extent.width() / full_extent.width())
        v = 1 - r / ((rows - 1) * extent.height() / full_extent.height())

        if nodata is not None:
            valid_mask = z_arr != nodata
        else:
            valid_mask = np.ones_like(z_arr, dtype=bool)

        # Combine all coordinates and remove NoData points
        vertices = np.column_stack((x.ravel(), y.ravel(), z.ravel()))[valid_mask.ravel()]   # (N_valid, 3)
        uvs = np.column_stack((u.ravel(), v.ravel()))[valid_mask.ravel()]                   # (N_valid, 2)

        # Assign vertex IDs to valid points and use -1 for NoData points
        grid_indices = np.full((rows, cols), -1, dtype=np.int32)    # np.int16 if rows * cols < 256 * 256
        grid_indices[valid_mask] = np.arange(np.sum(valid_mask))

        # Obtain the vertex IDs of the four corners of each cell using slicing
        p00 = grid_indices[:-1, :-1]
        p01 = grid_indices[:-1, 1:]
        p10 = grid_indices[1:, :-1]
        p11 = grid_indices[1:, 1:]

        # Split each cell into two triangles
        t1 = np.stack([p00, p10, p01], axis=-1).reshape(-1, 3)
        t2 = np.stack([p10, p11, p01], axis=-1).reshape(-1, 3)
        triangles = np.vstack([t1, t2])

        # Filter out triangles that contain at least one -1
        valid_triangles_mask = np.all(triangles >= 0, axis=1)
        faces = triangles[valid_triangles_mask]

        return self.exportBinaryChunks({
            "vertices": (vertices, np.float32),
            "indices": (faces, np.int32),
            "uvs": (uvs, np.float32)
        })

    def exportBinaryChunks(self, arrays):

        def nparr_to_bytes(arr, dtype=np.float32):
            return arr.astype(dtype, copy=False).tobytes()

        chunks = {
            key: nparr_to_bytes(arr, dtype) for key, (arr, dtype) in arrays.items()
        }

        if self.settings.isPreview:
            return {
                key: base64.b64encode(b).decode("ascii") for key, b in chunks.items()
            }

        tail = f"{self.blockIndex}.binjson"
        writeBinaryContainer(self.pathRoot + tail, chunks)

        return {
            "url": self.urlRoot + tail
        }


class DEMBlockResampBuilder(DEMBlockBuilderBase):

    def setup(self, blockIndex, extent: MapExtent, localOrigin: QgsPoint, grid_seg: QSize, roughness=1, edgeRoughness=1, clip_geometry=None, neighbors=None):
        super().setup(blockIndex, extent, localOrigin)

        self.grid_seg = grid_seg
        self.roughness = roughness
        self.edgeRoughness = edgeRoughness
        self.clip_geometry = clip_geometry
        self.neighbors = neighbors or []

        self.edges = None

    def build(self):
        """
        @returns {DEMBlockGridData}
        """
        c = self.extent.center()
        o = self.localOrigin

        b = {
            "type": "block",
            "layer": self.layer.jsLayerId,
            "block": self.blockIndex,
            "extent": self.extent.toDict(),
            "translate": [c.x() - o.x(), c.y() - o.y(), 0],
            "zScale": self.settings.mapTo3d().zScale
        }

        if self.clip_geometry:
            b["mesh"] = self.buildClippedMeshData(self.clip_geometry)

        else:
            columns, rows = (self.grid_seg.width() + 1, self.grid_seg.height() + 1)

            if self.edgeRoughness == 1 and len(self.neighbors) == 0:
                arr = self.provider.readAsArray(columns, rows, self.extent)
            else:
                grid_values = list(self.provider.readValues(columns, rows, self.extent))
                self.processEdgesCenter(grid_values, self.edgeRoughness)
                arr = np.array(grid_values, dtype=np.float32).reshape(rows, columns)

            b["grid"] = self.buildGridData(arr, self.extent, self.localOrigin, nodata=self.provider.nodata)

        return b

    def buildClippedMeshData(self, clip_geometry):
        """
        @returns {DEMMeshData}
        """
        transform_func = self.settings.mapTo3d().transformXY

        # create a grid geometry and split polygons with the grid
        grid = self.provider.readAsGridGeometry(self.grid_seg.width() + 1, self.grid_seg.height() + 1, self.extent)

        if self.extent.rotation():
            clip_geometry = QgsGeometry(clip_geometry)
            clip_geometry.rotate(self.extent.rotation(), self.extent.center())

        polys = grid.splitPolygon(clip_geometry)
        z_func = lambda x, y: grid.valueOnSurface(x, y) or 0

        tin = TINGeometry.fromQgsGeometry(polys, z_func, transform_func, centroid=False)
        d = tin.toDict(flat=True)

        return self.exportBinaryChunks({
            "vertices": (np.array(d["vertices"], dtype=np.float32), np.float32),
            "indices": (np.array(d["indices"], dtype=np.int32), np.int32)
        })

    def processEdges(self, grid_values, roughness):
        grid_width, grid_height = (self.grid_seg.width() + 1,
                                   self.grid_seg.height() + 1)

        for sx, sy, neighbor, roughness in self.neighbors:
            if self.roughness <= roughness:
                continue
            if neighbor.edges is None:
                logger.warning(f"Neighbor block {neighbor.blockIndex} has no edge values.")
                continue

            match (sx, sy):
                case (0, -1):
                    # top edge
                    for x in range(grid_width):
                        grid_values[x] = neighbor.edges[0][x]

                case (0, 1):
                    # bottom edge
                    offset = grid_width * (grid_height - 1)
                    for x in range(grid_width):
                        grid_values[offset + x] = neighbor.edges[3][x]

                case (-1, 0):
                    # right edge
                    offset = grid_width - 1
                    for y in range(grid_height):
                        grid_values[offset + grid_width * y] = neighbor.edges[1][y]

                case (1, 0):
                    # left edge
                    for y in range(grid_height):
                        grid_values[grid_width * y] = neighbor.edges[2][y]

                case (-1, -1):
                    # top-right corner
                    grid_values[grid_width - 1] = neighbor.edges[0][0]

                case (1, -1):
                    # top-left corner
                    grid_values[0] = neighbor.edges[0][grid_width - 1]

                case (-1, 1):
                    # bottom-right corner
                    grid_values[grid_width * grid_height - 1] = neighbor.edges[3][0]

                case (1, 1):
                    # bottom-left corner
                    grid_values[grid_width * (grid_height - 1)] = neighbor.edges[3][grid_width - 1]

                case _:
                    logger.warning(f"Edge processing: invalid sx and sy ({sx}, {sy})")

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


class DEMBlockRawBuilder(DEMBlockBuilderBase):

    def setup(self, blockIndex: int, tileExtent: MapExtent, localOrigin: QgsPoint, segments: int, dataExtentLowerRight, clip_geometry=None):
        super().setup(blockIndex, tileExtent, localOrigin)

        self.segments = segments
        self.tileSize = tileExtent.width()
        self.dataExtentLowerRight = dataExtentLowerRight
        self.clip_geometry = clip_geometry

    def build(self):
        """
        @returns {DEMBlockGridData}
        """
        c = self.extent.center()
        o = self.localOrigin

        b = {
            "type": "block",
            "layer": self.layer.jsLayerId,
            "block": self.blockIndex,
            "segments": self.segments,
            "extent": self.extent.toDict(),
            "translate": [c.x() - o.x(), c.y() - o.y(), 0],
            "zScale": self.settings.mapTo3d().zScale
        }

        if self.clip_geometry:
            # TODO: implement clipped tile
            pass

        else:
            segment_size = self.tileSize / self.segments
            half_segment_size = segment_size / 2

            # Determine the valid extent
            ulx, uly = self.extent.point(0, 1)              # A' (px is pt)
            tile_lrx, tile_lry = self.extent.point(1, 0)    # B' (px is pt)

            _lrx, _lry = self.dataExtentLowerRight              # C  (px is area)
            layer_lrx, layer_lry = _lrx - half_segment_size, _lry + half_segment_size # C' (px is pt)

            lrx, lry = min(layer_lrx, tile_lrx), max(layer_lry, tile_lry)

            valid_width = lrx - ulx
            valid_height = uly - lry
            center = QgsPointXY(ulx + valid_width / 2, uly - valid_height / 2)

            valid_extent = MapExtent(center, valid_width, valid_height)   # extent in the tile that contains actual data

            columns = int(valid_width / segment_size + 1)
            rows = int(valid_height / segment_size + 1)

            arr = self.provider.readAsArray(columns, rows, valid_extent)

            b["grid"] = self.buildGridData(arr, valid_extent, self.localOrigin, self.provider.nodata)

            # b["mesh"] = self.buildMeshData(arr, valid_extent, self.localOrigin, nodata=self.provider.nodata, full_extent=self.extent)
            # b["translate"] = [0, 0, 0]
        return b
