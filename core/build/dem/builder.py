# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import math
import os
from osgeo import gdal
from qgis.PyQt.QtCore import QSize
from qgis.core import QgsPoint, QgsProject

from .dem_builder import DEMResampBuilder, DEMRawBuilder
from .material_builder import DEMMaterialBuilder
from .property_reader import DEMPropertyReader
from .tileset import Tileset
from ..layerbuilderbase import LayerBuilderBase
from ...const import DEMMtlType
from ...exportsettings import BuildDEMOptions
from ...geometry import dissolvePolygonsWithinExtent
from ...mapextent import MapExtent, ZRange
from ....conf import DEBUG_MODE, DEF_SETS, GRID_DEM_OUTPUT_MODE
from ....utils.basic import  parseFloat
from ....utils.file import mkpath
from ....utils.js import hex_color
from ....utils.logging import logger


class BuildTask:
    def __init__(self, builder, discardResult=False):
        self.builder = builder
        self.discardResult = discardResult

    def build(self):
        data = self.builder.build()
        return None if self.discardResult else data


class TileIdTask:
    def __init__(self, tile):
        self.tile = tile

    def build(self):
        return f"{self.tile.level}/{self.tile.x}/{self.tile.y}"


class DataTask:
    def __init__(self, data):
        self.data = data

    def build(self):
        return self.data


class BuildResultSet:
    def __init__(self, discardResult=False):
        self.results = {}
        self.discardResult = discardResult

    def add(self, data, dataKey=""):
        if not dataKey:
            return

        if dataKey.endswith("[]"):
            self.results.setdefault(dataKey[:-2], []).append(data)
        else:
            self.results[dataKey] = data

    def build(self):
        return None if self.discardResult else self.results


class DEMLayerBuilder(LayerBuilderBase):
    """Generates the export data for a DEM layer."""

    def __init__(self, layer, settings, imageManager, buildOptions=None, assetDestination=None, progress=None, log=None):
        """See `LayerBuilderBase.__init__()` for argument details."""
        super().__init__(layer, settings, imageManager, buildOptions, assetDestination, progress, log)

        self.buildOptions = self.buildOptions or BuildDEMOptions()
        self.mtlBuilder = DEMMaterialBuilder(layer, settings, imageManager, assetDestination)
        self.provider = settings.demProviderByLayerId(layer.layerId)

        if self.properties.get("radioButton_OriginalValues") or self.properties.get("radioButton_Pyramid"):
            BldClass = DEMRawBuilder
        else:
            BldClass = DEMResampBuilder

        self.demBuilder = BldClass(layer, settings, self.provider, self.mtlBuilder.materialManager, self.assetDestination)

        self._tileset = None

    def build(self, build_contents=False):
        """
        Generate the export data for this DEM layer.

        Args:
            build_contents (bool): If True, construct and return DEM blocks / tiles.

        @returns {DEMLayerData}
        """
        if self.provider is None:
            return None

        if self.buildOptions.onlyMaterial:
            return None     # do not send "layer" data

        d = {
            "type": "layer",
            "id": self.layer.jsLayerId,
            "properties": self.layerProperties()
        }

        if self.properties.get("radioButton_Pyramid"):
            tileset = self._getTileset()
            if tileset:
                d["tileset"] = tileset.metadata()

                # with open("D:/tileset.json", "w", encoding="ascii") as f:
                #     f.write(tileset.metadata(asJson=True))
            else:
                logger.error("Failed to create a tileset.")

        if build_contents:
            d["body"] = {
                "contents": list(self.buildContents())
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
        p["mtlIndex"] = self.layer.mtlIndex(self.properties.get("mtlId"))

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

        layer_grid = self.provider.grid()

        target_grid = layer_grid
        if not self.properties.get("radioButton_NoClip"):
            be = self.settings.baseExtent()
            target_grid = target_grid.intersection(be.unrotatedRect())
            if not target_grid:
                return None

        stats = self.layer.mapLayer.dataProvider().bandStatistics(1)
        zrange = ZRange(stats.minimumValue, stats.maximumValue)

        args = (self.layer.jsLayerId, target_grid, zrange, self.settings.mapTo3d().origin)

        self._tileset = Tileset(*args) if tileSegments is None else Tileset(*args, tileSegments=tileSegments)
        return self._tileset

    def buildTasks(self):
        """Yield build tasks that produce DEM tiles and materials."""
        pyramid = self.properties.get("radioButton_Pyramid")
        tiles = self.properties.get("radioButton_OriginalValues")

        if pyramid or tiles:
            if not self.provider.CanUseOriginalValues:
                logger.error("DEM provider doesn't support providing original values.")
                return

            self.provider.setResampleAlg(gdal.GRA_NearestNeighbour)

            if pyramid:
                if self.settings.isPreview:
                    yield from self._buildTasks_PyramidTilePreview()
                else:
                    yield from self._buildTasks_PyramidTileExport()
            else:
                segments = self.properties.get("spinBox_TileSideSegments", 512)
                yield from self._buildTasks_Raw(segments)

            return

        self.provider.setResampleAlg(gdal.GRA_Bilinear)
        yield from self._buildTasks_Resamp()

    def _buildTasks_PyramidTilePreview(self):
        if self.buildOptions.onlyMaterial:
            yield DataTask({
                "type": "signal",
                "name": "tileMtlChanged",
                "layer": self.layer.jsLayerId
            })

    def _buildTasks_PyramidTileExport(self, minLevel=0):
        """
        @yields {DEMTileEntry} builder
        """
        materials = self.properties.get("materials", [])
        tasksPerSet = 2 + len(materials)
        results = None

        for i, task in enumerate(self._buildTasks_Raw(minLevel=minLevel)):
            m = i % tasksPerSet
            if m == 0:
                if results:
                    yield results

                results = BuildResultSet()
                dataKey = "tileId"
            elif m == 2:
                dataKey = "grid"
            else:
                dataKey = "materials[]"

            results.add(task.build(), dataKey)

        if results:
            yield results

    def _buildTasks_Raw(self, segments=128, minLevel=None):
        tileset = self._getTileset(segments)
        if not tileset:
            logger.error("Failed to create a tileset.")
            return

        isPyramid = bool(minLevel is not None)

        if self.settings.isPreview:
            dest = None
        else:
            dest = self.assetDestination.clone()
            if isPyramid:
                self.assetDestination.filePrefix = ""

        materials = self.properties.get("materials", [])
        mtlCount = len(materials)
        currentMtlId = self.properties.get("mtlId")

        asBlock = not isPyramid
        debugText = ""

        tiles = list(tileset.iterTiles(minLevel))
        tileCount = len(tiles)
        for i, tile in enumerate(tiles):
            if isPyramid:
                yield TileIdTask(tile)

            if DEBUG_MODE:
                debugText = f"{tile.level}/{tile.x}/{tile.y}"

            tileExtent = MapExtent.fromRect(tile.rect)

            dataRect = tile.rect.intersect(tileset.boundingRect)
            dataExtent = MapExtent.fromRect(dataRect)

            if dest and isPyramid:
                self.assetDestination.outputDir = os.path.join(*map(str, (dest.outputDir, self.layer.jsLayerId, tile.level, tile.x)))
                self.assetDestination.baseUrl = f"{dest.baseUrl}{self.layer.jsLayerId}/{tile.level}/{tile.x}/"
                mkpath(self.assetDestination.outputDir)
                blockIndex = tile.y
            else:
                blockIndex = i

            # set up material builder for first/current material
            if self.buildOptions.allMaterials and mtlCount:
                id = materials[0].get("id")
                self.mtlBuilder.setup(blockIndex, tileExtent, dataExtent=dataExtent, mtlId=id, asBlock=asBlock, useNow=bool(id == currentMtlId), debugText=debugText)
            else:
                self.mtlBuilder.setup(blockIndex, tileExtent, dataExtent=dataExtent, asBlock=asBlock, useNow=True, debugText=debugText)
            yield BuildTask(self.mtlBuilder)

            # set up dem builder
            if not self.buildOptions.onlyMaterial:
                # DEMRawBuilder
                self.demBuilder.setup(blockIndex, tileExtent, self.settings.mapTo3d().origin, segments, dataExtent=dataExtent, asBlock=asBlock)
                yield BuildTask(self.demBuilder)

            # set up material builder for remaininig materials
            if self.buildOptions.allMaterials:
                for idx in range(1, mtlCount):
                    id = materials[idx].get("id")
                    self.mtlBuilder.setup(blockIndex, tileExtent, dataExtent=dataExtent, mtlId=id, asBlock=asBlock, useNow=bool(id == currentMtlId), debugText=debugText)
                    yield BuildTask(self.mtlBuilder)

            self.progress(i + 1, tileCount)

        if dest:
            dest.copyTo(self.assetDestination)

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

        centerBlk = DEMResampBuilder(self.layer, self.settings, self.provider, self.mtlBuilder.materialManager, self.assetDestination)
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
            if self.buildOptions.allMaterials and mtlCount:
                id = materials[0].get("id")
                self.mtlBuilder.setup(blockIndex, extent, mtlId=id, useNow=bool(id == currentMtlId))
            else:
                self.mtlBuilder.setup(blockIndex, extent, useNow=True)
            yield BuildTask(self.mtlBuilder)

            # set up grid builder
            if not self.buildOptions.onlyMaterial:
                neighbors = None
                if is_center:
                    blkBuilder = centerBlk
                else:
                    blkBuilder = self.demBuilder
                    if sx * sx <= 1 and sy * sy <= 1:
                        neighbors = [(sx, sy, centerBlk, 1)]

                # DEMResampBuilder
                blkBuilder.setup(blockIndex, extent, self.settings.mapTo3d().origin, grid_seg,
                                 roughness=1 if is_center else roughness,
                                 edgeRoughness=roughness if is_center else 1,
                                 clip_geometry=clip_geometry if is_center else None,
                                 neighbors=neighbors)
                yield BuildTask(blkBuilder)

            # set up material builder for remaininig materials
            if self.buildOptions.allMaterials:
                for idx in range(1, mtlCount):
                    id = materials[idx].get("id")
                    self.mtlBuilder.setup(blockIndex, extent, mtlId=id, useNow=bool(id == currentMtlId))
                    yield BuildTask(self.mtlBuilder)

            self.progress(i + 1, size2)

    def buildTile(self, url, level, x, y, onlyMaterial=False):
        """
        @returns {TileDataResponse}
        """
        tileset = self._getTileset()

        tileRect = tileset.tileRect(level, x, y)
        tileExtent = MapExtent.fromRect(tileRect)

        dataRect = tileRect.intersect(tileset.boundingRect)
        dataExtent = MapExtent.fromRect(dataRect)

        data = {}
        if not onlyMaterial:
            self.demBuilder.setup(0, tileExtent, self.settings.mapTo3d().origin, tileset.tileSegments, dataExtent=dataExtent, asBlock=False)
            data["grid"] = self.demBuilder.build()

        self.mtlBuilder.setup(0, tileExtent, asBlock=False, debugText=f"{level}/{x}/{y}" if DEBUG_MODE else "")
        data["material"] = self.mtlBuilder.build()

        return {
            "type": "tile",
            "layer": self.layer.jsLayerId,
            "url": url,
            "data": data    # as {DEMTileData}
        }
