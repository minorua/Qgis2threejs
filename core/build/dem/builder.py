# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import math
import base64
from osgeo import gdal
from qgis.PyQt.QtCore import QBuffer, QIODevice, QSize
from qgis.PyQt.QtGui import QImage, QPainter, QFont, QColor
from qgis.core import QgsPoint, QgsProject

from .block_builder import DEMBlockResampBuilder, DEMBlockRawBuilder
from .material_builder import DEMMaterialBuilder
from .property_reader import DEMPropertyReader
from .tileset import Tileset
from ..layerbuilderbase import LayerBuilderBase
from ...const import DEMMtlType
from ...geometry import dissolvePolygonsWithinExtent
from ...mapextent import MapExtent, ZRange
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

        if self.properties.get("radioButton_OriginalValues") or self.properties.get("radioButton_Pyramid"):
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
            if tileset:
                d["tileset"] = tileset.metadata()

                # with open("D:/tileset.json", "w", encoding="ascii") as f:
                #     f.write(tileset.metadata(asJson=True))
            else:
                logger.error("Failed to create a tileset.")

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

    def _getTileset(self, tileSegments=None):
        if self._tileset:
            return self._tileset

        geotransform = self.provider.geotransform()
        if not math.isclose(geotransform[1], -geotransform[5]):
            logger.error(f"{self.layer.name}: DEM pixel size is different in X and Y directions.")
            return None

        # DEM provider is assumed to be GDALDEMProvider.
        layer_grid = self.provider.grid()

        target_grid = layer_grid
        if not self.properties.get("radioButton_NoClip"):
            be = self.settings.baseExtent()
            target_grid = target_grid.intersection(be.unrotatedRect())
            if not target_grid:
                return None

        zrange = ZRange(0, 1000)        # TODO:
        args = (self.layer.jsLayerId, target_grid, zrange, self.settings.mapTo3d().origin)

        self._tileset = Tileset(*args) if tileSegments is None else Tileset(*args, tileSegments=tileSegments)
        return self._tileset

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
        segments = self.properties.get("spinBox_TileSideSegments", 512)
        tileset = self._getTileset(segments)
        if not tileset:
            logger.error("Failed to create a tileset.")
            return

        materials = self.properties.get("materials", [])
        mtlCount = len(materials)
        currentMtlId = self.properties.get("mtlId")

        for blockIndex, tileRect in enumerate(tileset.iterMaxLevelTileRects()):
                tileExtent = MapExtent.fromRect(tileRect)

                validRect = tileRect.intersect(tileset.boundingRect)
                validExtent = MapExtent.fromRect(validRect)

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

                self.progress(blockIndex + 1, tileset.tileShape.cols * tileset.tileShape.rows)

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

        tileRect = tileset.tileRect(level, x, y)
        tileExtent = MapExtent.fromRect(tileRect)

        validRect = tileRect.intersect(tileset.boundingRect)
        validExtent = MapExtent.fromRect(validRect)

        self.blockBuilder.setup(0, tileExtent, self.settings.mapTo3d().origin, tileset.tileSegments, validExtent=validExtent)
        grid = self.blockBuilder.build()

        self.mtlBuilder.setup(0, tileExtent, debugText=f"{level}/{x}/{y}")
        mtl = self.mtlBuilder.build().get("materials", [{}])[0]

        o = self.settings.mapTo3d().origin
        extent = grid["extent"]
        cx, cy = extent["cx"] - o.x(), extent["cy"] - o.y()     # in 3d world coordinates

        return {
            "type": "tile",
            "layer": self.layer.jsLayerId,
            "url": url,
            "data": {
                "grid": grid,
                "material": mtl,
                "translate": [cx, cy, 0]
            }
        }
