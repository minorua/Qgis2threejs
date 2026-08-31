# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import math
import base64
from osgeo import gdal
from qgis.PyQt.QtCore import QBuffer, QIODevice, QSize
from qgis.PyQt.QtGui import QImage, QPainter, QFont, QColor
from qgis.core import QgsPoint, QgsPointXY, QgsProject

from .block_builder import DEMBlockResampBuilder, DEMBlockRawBuilder
from .material_builder import DEMMaterialBuilder
from .property_reader import DEMPropertyReader
from .tileset import Tileset
from ..layerbuilderbase import LayerBuilderBase
from ...boundingvolume import BoundingVolume
from ...const import DEMMtlType
from ...geometry import dissolvePolygonsWithinExtent
from ...mapextent import MapExtent
from ....conf import DEF_SETS, GRID_DEM_OUTPUT_MODE
from ....utils.basic import  parseFloat
from ....utils.js import hex_color
from ....utils.logging import logger


class DEMLayerBuilder(LayerBuilderBase):
    """Generates the export data for a DEM layer."""

    def __init__(self, layer, settings, imageManager, assetDestination=None, progress=None, log=None):
        """See `LayerBuilderBase.__init__()` for argument details."""
        super().__init__(layer, settings, imageManager, assetDestination, progress, log)

        self.provider = settings.demProviderByLayerId(layer.layerId)
        self.mtlBuilder = DEMMaterialBuilder(layer, settings, imageManager, assetDestination)

        if self.properties.get("radioButton_OriginalValues"):
            BldClass = DEMBlockRawBuilder
        elif self.properties.get("radioButton_Pyramid"):
            BldClass = DEMBlockRawBuilder
        else:
            BldClass = DEMBlockResampBuilder

        self.blockBuilder = BldClass(layer, settings, self.provider, self.mtlBuilder.materialManager, self.assetDestination)

        self._tileset = None

    def build(self, build_blocks=False):
        """
        Generate the export data for this DEM layer.

        Args:
            build_blocks (bool): If True, construct and return DEM blocks under `data['body']['blocks']`.

        @returns {DEMLayerData}
        """
        if self.provider is None:
            return None

        if self.layer.opt.onlyMaterial:
            return None     # do not send "layer" data

        d = {
            "type": "layer",
            "id": self.layer.jsLayerId,
            "properties": self.layerProperties()
        }

        pyramid = self.properties.get("radioButton_Pyramid")
        if pyramid and self.provider.CanUseOriginalValues:
            self.provider.setResampleAlg(gdal.GRA_NearestNeighbour)

            tileset = self._getTileset()
            d["tileset"] = tileset.metadata()

            # with open("D:/tileset.json", "w", encoding="ascii") as f:
            #     f.write(tileset.metadata(asJson=True))

        if build_blocks:
            d["body"] = {
                "blocks": list(self.buildBlocks())
            }

        # d["PROPERTIES"] = self.properties

        return d

    def layerProperties(self):
        """
        @returns {DEMLayerProperties}
        """
        p = LayerBuilderBase.layerProperties(self)
        p["type"] = "dem"
        p["dataType"] = "mesh" if self.properties.get("radioButton_ClipPolygon") else GRID_DEM_OUTPUT_MODE
        p["mtlNames"] = [mtl.get("name", "") for mtl in self.properties.get("materials", [])]
        p["mtlIdx"] = self.layer.mtlIndex(self.properties.get("mtlId"))

        # auxiliary objects
        opacity = DEMPropertyReader.opacity(self.properties)
        mtlMan = self.mtlBuilder.materialManager

        if self.properties.get("checkBox_Sides"):
            mi = mtlMan.getMeshIndex(color=hex_color(self.properties.get("colorButton_Side", DEF_SETS.SIDE_COLOR), prefix="0x"), opacity=opacity, doubleSide=True)
            p["sides"] = {
                "mtl": mtlMan.build(mi),
                "bottom": parseFloat(self.properties.get("lineEdit_Bottom"), DEF_SETS.Z_BOTTOM)
            }

        return p

    def buildTasks(self):
        """Yield build tasks that produce DEM tiles and materials."""
        if self.properties.get("radioButton_Pyramid"):
            return

        if self.properties.get("radioButton_OriginalValues"):
            if not self.provider.CanUseOriginalValues:
                logger.error("DEM provider doesn't support providing original values.")
                return

            self.provider.setResampleAlg(gdal.GRA_NearestNeighbour)
            yield from self._buildTasks_Raw()
            return

        self.provider.setResampleAlg(gdal.GRA_Bilinear)
        yield from self._buildTasks_Resamp()

    def _buildTasks_Raw(self):
        be = self.settings.baseExtent()

        materials = self.properties.get("materials", [])
        mtlCount = len(materials)
        currentMtlId = self.properties.get("mtlId")

        segments = self.properties.get("spinBox_TileSideSegments", 512)
        noClip = self.properties.get("radioButton_NoClip")

        # DEM provider is assumed to be GDALDEMProvider.
        layer_extent = self.provider.extent()

        if noClip:
            gt = self.provider.geotransform()
            ulx, uly = gt[0], gt[3]
            xres, yres = gt[1], -gt[5]

            tile_cols = math.ceil((self.provider.width - 1) / segments)
            tile_rows = math.ceil((self.provider.height - 1) / segments)

            lrx, lry = layer_extent.point(1, 0)     # C  (px is area)
        else:
            # clip to base extent
            layer_grect = self.provider.gridRectangle()
            grect = layer_grect.intersect(be.unrotatedRect())
            if grect is None:
                return

            ulx, uly = grect.rect.xMinimum(), grect.rect.yMaximum()
            xres, yres = grect.grid.xres, grect.grid.yres

            tile_cols = math.ceil((grect.columns() - 1) / segments)
            tile_rows = math.ceil((grect.rows() - 1) / segments)

            lrx, lry = grect.rect.xMaximum(), grect.rect.yMinimum()     # C  (px is area)

        layer_lrx, layer_lry = lrx - xres / 2, lry + yres / 2  # C' (px is pt)

        if not math.isclose(xres, yres):
            logger.error(f"{self.layer.name}: DEM pixel size is different in X and Y directions.")
            return

        tile_size = xres * segments
        tiles = []
        for row in range(tile_rows):
            for col in range(tile_cols):
                blockIndex = row * tile_cols + col

                cx = ulx + xres / 2 + (col + 0.5) * tile_size
                cy = uly - yres / 2 - (row + 0.5) * tile_size
                tileExtent = MapExtent(QgsPoint(cx, cy), tile_size, tile_size)

                tiles.append((-row, blockIndex, tileExtent))

        for i, (_r, blockIndex, tileExtent) in enumerate(sorted(tiles)):
                # determine the valid extent - the extent of the tile that contains data
                ulx, uly = tileExtent.point(0, 1)              # A' (px is pt)
                tile_lrx, tile_lry = tileExtent.point(1, 0)    # B' (px is pt)

                valid_width = min(layer_lrx, tile_lrx) - ulx
                valid_height = uly - max(layer_lry, tile_lry)
                center = QgsPointXY(ulx + valid_width / 2, uly - valid_height / 2)

                validExtent = MapExtent(center, valid_width, valid_height)

                # set up material builder for first/current material
                if self.layer.opt.allMaterials and len(materials):
                    id = materials[0].get("id")
                    self.mtlBuilder.setup(blockIndex, tileExtent, validExtent=validExtent, mtlId=id, useNow=bool(id == currentMtlId))
                else:
                    self.mtlBuilder.setup(blockIndex, tileExtent, useNow=True)
                yield self.mtlBuilder

                # set up grid builder
                if not self.layer.opt.onlyMaterial:
                    # DEMBlockRawBuilder
                    self.blockBuilder.setup(blockIndex, tileExtent, self.settings.mapTo3d().origin, segments, validExtent=validExtent)
                    yield self.blockBuilder

                # set up material builder for remaininig materials
                if self.layer.opt.allMaterials:
                    for idx in range(1, mtlCount):
                        id = materials[idx].get("id")
                        self.mtlBuilder.setup(blockIndex, tileExtent, validExtent=validExtent, mtlId=id, useNow=bool(id == currentMtlId))
                        yield self.mtlBuilder

                self.progress(i + 1, tile_cols * tile_rows)

    def _getTileset(self):
        if self._tileset:
            return self._tileset

        be = self.settings.baseExtent()

        materials = self.properties.get("materials", [])
        mtlCount = len(materials)
        currentMtlId = self.properties.get("mtlId")

        segments = self.properties.get("spinBox_TileSideSegments", 512)
        noClip = self.properties.get("radioButton_NoClip")

        # DEM provider is assumed to be GDALDEMProvider.
        layer_extent = self.provider.extent()

        layer_grect = self.provider.gridRectangle()
        if noClip:
            grect = layer_grect
        else:
            # clip to base extent
            grect = layer_grect.intersect(be.unrotatedRect())
            if grect is None:
                return

        ulx, uly = grect.rect.xMinimum(), grect.rect.yMaximum()
        xres, yres = grect.grid.xres, grect.grid.yres

        cols = grect.columns() - 1
        rows = grect.rows() - 1

        lrx, lry = grect.rect.xMaximum(), grect.rect.yMinimum()     # C  (px is area)

        layer_xmax, layer_ymin = lrx - xres / 2, lry + yres / 2  # C' (px is pt)

        if not math.isclose(xres, yres):
            logger.error(f"{self.layer.name}: DEM pixel size is different in X and Y directions.")
            return

        layer_xmin = ulx + xres / 2
        layer_ymax = uly - yres / 2
        zmin = 0
        zmax = 1000
        boundingVolume = BoundingVolume(layer_xmin, layer_ymin, zmin,
                                        layer_xmax, layer_ymax, zmax)

        self._tileset = Tileset(self.layer.jsLayerId, cols, rows, boundingVolume, self.settings.mapTo3d().origin)
        return self._tileset

    def _buildTasks_Resamp(self):
        materials = self.properties.get("materials", [])
        mtlCount = len(materials)
        currentMtlId = self.properties.get("mtlId")

        be = self.settings.baseExtent()
        if self.mtlBuilder.currentMtlType() in (DEMMtlType.LAYER, DEMMtlType.MAPCANVAS):
            # calculate extent with the same aspect ratio as current material texture image
            tex_size = DEMPropertyReader.textureSize(self.mtlBuilder.currentMtlProperties(), be, self.settings)
            be = MapExtent(be.center(), be.width(), be.width() * tex_size.height() / tex_size.width(), be.rotation())

        base_grid_seg = self.settings.demGridSegments(self.layer.layerId)

        # clipping
        clip_geometry = None
        clipping = self.properties.get("radioButton_ClipPolygon")
        if clipping:
            clip_layerId = self.properties.get("comboBox_ClipLayer")
            clip_layer = QgsProject.instance().mapLayer(clip_layerId) if clip_layerId else None
            if clip_layer:
                clip_geometry = dissolvePolygonsWithinExtent(clip_layer, be, self.settings.crs)

        # surrounding tiles
        tiles = self.properties.get("checkBox_Tiles", False)
        roughness = self.properties.get("spinBox_Roughening", 1) if tiles else 1
        size = self.properties.get("spinBox_Size", 1) if tiles else 1
        size2 = size * size

        centerBlk = DEMBlockResampBuilder(self.layer, self.settings, self.provider, self.mtlBuilder.materialManager, self.assetDestination)
        blks = []
        for i in range(size2):
            sx = i % size - (size - 1) // 2
            sy = i // size - (size - 1) // 2
            dist2 = sx * sx + sy * sy
            blks.append([dist2, -sy, sx, sy, i])

        for i, (dist2, _nsy, sx, sy, blockIndex) in enumerate(sorted(blks)):
            is_center = (sx == 0 and sy == 0)
            if is_center:
                extent = be
                grid_seg = base_grid_seg
            else:
                block_center = QgsPoint(be.center().x() + sx * be.width(),
                                        be.center().y() + sy * be.height())
                extent = MapExtent(block_center, be.width(), be.height())
                grid_seg = QSize(max(1, base_grid_seg.width() // roughness),
                                 max(1, base_grid_seg.height() // roughness))

            # set up material builder for first/current material
            if self.layer.opt.allMaterials and len(materials):
                id = materials[0].get("id")
                self.mtlBuilder.setup(blockIndex, extent, mtlId=id, useNow=bool(id == currentMtlId))
            else:
                self.mtlBuilder.setup(blockIndex, extent, useNow=True)
            yield self.mtlBuilder

            # set up grid builder
            if not self.layer.opt.onlyMaterial:
                neighbors = None
                if is_center:
                    blkBuilder = centerBlk
                else:
                    blkBuilder = self.blockBuilder
                    if sx * sx <= 1 and sy * sy <= 1:
                        neighbors = [(sx, sy, centerBlk, 1)]

                # DEMBlockResampBuilder
                blkBuilder.setup(blockIndex, extent, self.settings.mapTo3d().origin, grid_seg,
                                 roughness=1 if is_center else roughness,
                                 edgeRoughness=roughness if is_center else 1,
                                 clip_geometry=clip_geometry if is_center else None,
                                 neighbors=neighbors)
                yield blkBuilder

            # set up material builder for remaininig materials
            if self.layer.opt.allMaterials:
                for idx in range(1, mtlCount):
                    id = materials[idx].get("id")
                    self.mtlBuilder.setup(blockIndex, extent, mtlId=id, useNow=bool(id == currentMtlId))
                    yield self.mtlBuilder

            self.progress(i + 1, size2)

    def buildTile(self, url, level, x, y):
        tileset = self._getTileset()
        tileExtent = tileset.tileExtent(level, x, y)

        # determine the valid extent - the extent of the tile that contains data
        ulx, uly = tileExtent.point(0, 1)              # A' (px is pt)
        tile_lrx, tile_lry = tileExtent.point(1, 0)    # B' (px is pt)

        # TODO: There may be blank area at the top and on the right.
        # valid_width = min(layer_lrx, tile_lrx) - ulx
        # valid_height = uly - max(layer_lry, tile_lry)
        valid_width, valid_height = tileExtent.width(), tileExtent.height()

        center = QgsPointXY(ulx + valid_width / 2, uly - valid_height / 2)
        validExtent = MapExtent(center, valid_width, valid_height)

        self.blockBuilder.setup(0, tileExtent, self.settings.mapTo3d().origin, tileset.TILE_SEGMENTS, validExtent=validExtent)
        grid = self.blockBuilder.build()

        self.mtlBuilder.setup(0, tileExtent)
        mtl = self.mtlBuilder.build().get("materials", [{}])[0]
        base64img = mtl.get("image", {}).get("base64")
        if base64img:
            base64img = add_text_to_base64_image(base64img, f"{level}/{x}/{y}")
            mtl["image"]["base64"] = base64img

        return {
            "type": "tile",
            "layer": self.layer.jsLayerId,
            "url": url,
            "data": {
                "level": level,
                "x": x,
                "y": y,
                "grid": grid,
                "material": mtl
            }
        }


def add_text_to_base64_image(base64_string, text, position=(10, 10), font_size=64, color=(255, 255, 0)):
    if not base64_string:
        return base64_string

    base64_data = base64_string.replace("data:image/jpeg;base64,", "").replace("data:image/png;base64,", "").replace("data:image/webp;base64,", "")
    image_data = base64.b64decode(base64_data)

    img = QImage()
    img.loadFromData(image_data)

    if img.isNull():
        logger.warning("Failed to load image from base64 data")
        return base64_string

    font = QFont()
    font.setPointSize(font_size)

    painter = QPainter(img)
    painter.setFont(font)
    painter.setPen(QColor(*color))
    painter.drawText(position[0], position[1] + font_size, text)
    painter.end()

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "JPEG")
    image_bytes = buffer.data().data()
    buffer.close()

    encoded = base64.b64encode(image_bytes).decode()
    return f"data:image/jpeg;base64,{encoded}"
