# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import math
from osgeo import gdal
from qgis.PyQt.QtCore import QSize
from qgis.core import QgsPoint, QgsProject

from .grid_builder import DEMGridBuilder, DEMTileGridBuilder
from .material_builder import DEMMaterialBuilder
from .property_reader import DEMPropertyReader
from ..layerbuilderbase import LayerBuilderBase
from ...const import DEMMtlType
from ...geometry import dissolvePolygonsWithinExtent
from ...mapextent import MapExtent
from ....conf import DEBUG_MODE, DEF_SETS
from ....utils import hex_color, logger, parseFloat



class DEMLayerBuilder(LayerBuilderBase):
    """Generates the export data structure for a DEM layer.

    This builder coordinates grid builders and material builders to produce
    a DEM block or tiled DEM blocks. It supports optional clipping to vector
    polygons, tiled surrounding blocks, and multiple materials.
    """

    def __init__(self, layer, settings, imageManager, pathRoot=None, urlRoot=None, progress=None, log=None):
        """See `LayerBuilderBase.__init__()` for argument details."""
        super().__init__(layer, settings, imageManager, pathRoot, urlRoot, progress, log)

        self.provider = settings.demProviderByLayerId(layer.layerId)
        self.mtlBuilder = DEMMaterialBuilder(layer, settings, imageManager, pathRoot, urlRoot)

        gridBldClass = DEMTileGridBuilder if self.properties.get("radioButton_OriginalValues") else DEMGridBuilder
        self.grdBuilder = gridBldClass(layer, settings, self.provider, self.mtlBuilder.materialManager, self.pathRoot, self.urlRoot)

    def build(self, build_blocks=False):
        """Generate the export data structure for this DEM layer.

        Args:
            build_blocks (bool): If True, construct and return DEM blocks under `data['body']['blocks']`.

        Returns:
            dict: Layer export data.
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

        if build_blocks:
            d["body"] = {
                "blocks": list(self.buildBlocks())
            }

        if DEBUG_MODE:
            d["PROPERTIES"] = self.properties

        return d

    def layerProperties(self):
        """Return layer properties specific to this DEM layer."""
        p = LayerBuilderBase.layerProperties(self)
        p["type"] = "dem"
        p["clipped"] = self.properties.get("radioButton_ClipPolygon", False)
        p["tiled"] = self.properties.get("radioButton_OriginalValues", False)
        p["mtlNames"] = [mtl.get("name", "") for mtl in self.properties.get("materials", [])]
        p["mtlIdx"] = self.layer.mtlIndex(self.properties.get("mtlId"))

        # auxiliary objects
        opacity = DEMPropertyReader.opacity(self.properties)
        mtlMan = self.mtlBuilder.materialManager

        if self.properties.get("checkBox_Sides"):
            mi = mtlMan.getMeshMaterialIndex(hex_color(self.properties.get("colorButton_Side", DEF_SETS.SIDE_COLOR), prefix="0x"), opacity)
            p["sides"] = {"mtl": mtlMan.build(mi),
                          "bottom": parseFloat(self.properties.get("lineEdit_Bottom"), DEF_SETS.Z_BOTTOM)}

        if self.properties.get("checkBox_Frame") and not self.properties.get("radioButton_ClipPolygon"):
            mi = mtlMan.getLineIndex(hex_color(self.properties.get("colorButton_Edge", DEF_SETS.EDGE_COLOR), prefix="0x"), opacity)
            p["edges"] = {"mtl": mtlMan.build(mi)}

        if self.properties.get("checkBox_Wireframe"):
            mi = mtlMan.getLineIndex(hex_color(self.properties.get("colorButton_Wireframe", DEF_SETS.WIREFRAME_COLOR), prefix="0x"), opacity)
            p["wireframe"] = {"mtl": mtlMan.build(mi)}

        return p

    def buildTasks(self):
        """Yield build tasks that produce DEM tiles and materials."""
        orig = self.properties.get("radioButton_OriginalValues")

        if orig and self.provider.CanUseOriginalValues:
            self.provider.setResampleAlg(gdal.GRA_NearestNeighbour)
            yield from self._buildTasks_Orig()
        else:
            self.provider.setResampleAlg(gdal.GRA_Bilinear)
            yield from self._buildTasks_Resamp()

    def _buildTasks_Orig(self):
        materials = self.properties.get("materials", [])
        mtlCount = len(materials)
        currentMtlId = self.properties.get("mtlId")

        be = self.settings.baseExtent()
        if be.rotation():
            logger.error(f'{self.layer.name}: Map rotation is not supported when using the "Use original values" option.')
            return

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

            data_extent_lr = layer_extent.point(1, 0)
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

            data_extent_lr = grect.rect.xMaximum(), grect.rect.yMinimum()

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
                tile_extent = MapExtent(QgsPoint(cx, cy), tile_size, tile_size)

                tiles.append((blockIndex, tile_extent, (cx, cy)))

        beCenterX, beCenterY = be.center().x(), be.center().y()
        for blockIndex, tile_extent, tile_center in tiles:
                # set up material builder for first/current material
                if self.layer.opt.allMaterials and len(materials):
                    id = materials[0].get("id")
                    self.mtlBuilder.setup(blockIndex, tile_extent, id, useNow=bool(id == currentMtlId))
                else:
                    self.mtlBuilder.setup(blockIndex, tile_extent, useNow=True)
                yield self.mtlBuilder

                # set up grid builder
                if not self.layer.opt.onlyMaterial:
                    # DEMTileGridBuilder
                    self.grdBuilder.setup(blockIndex,
                                          segments=segments,
                                          tileExtent=tile_extent,
                                          offsetX=tile_center[0] - beCenterX,
                                          offsetY=tile_center[1] - beCenterY,
                                          dataExtentLowerRight=data_extent_lr)
                    yield self.grdBuilder

                # set up material builder for remaininig materials
                if self.layer.opt.allMaterials:
                    for idx in range(1, mtlCount):
                        id = materials[idx].get("id")
                        self.mtlBuilder.setup(blockIndex, tile_extent, id, useNow=bool(id == currentMtlId))
                        yield self.mtlBuilder

                self.progress(blockIndex + 1, tile_cols * tile_rows)

    def _buildTasks_Resamp(self):
        be = self.settings.baseExtent()

        materials = self.properties.get("materials", [])
        mtlCount = len(materials)
        currentMtlId = self.properties.get("mtlId")

        if self.mtlBuilder.currentMtlType() in (DEMMtlType.LAYER, DEMMtlType.MAPCANVAS):
            # calculate extent with the same aspect ratio as current material texture image
            tex_size = DEMPropertyReader.textureSize(self.mtlBuilder.currentMtlProperties(), be, self.settings)
            be = MapExtent(be.center(), be.width(), be.width() * tex_size.height() / tex_size.width(), be.rotation())

        planeWidth, planeHeight = (be.width(), be.height())

        center = be.center()
        rotation = be.rotation()
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

        centerBlk = DEMGridBuilder(self.layer, self.settings, self.provider, self.mtlBuilder.materialManager, self.pathRoot, self.urlRoot)
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
                block_center = QgsPoint(center.x() + sx * be.width(), center.y() + sy * be.height())
                extent = MapExtent(block_center, be.width(), be.height()).rotate(rotation, center)
                grid_seg = QSize(max(1, base_grid_seg.width() // roughness),
                                 max(1, base_grid_seg.height() // roughness))

            # set up material builder for first/current material
            if self.layer.opt.allMaterials and len(materials):
                id = materials[0].get("id")
                self.mtlBuilder.setup(blockIndex, extent, id, useNow=bool(id == currentMtlId))
            else:
                self.mtlBuilder.setup(blockIndex, extent, useNow=True)
            yield self.mtlBuilder

            # set up grid builder
            if not self.layer.opt.onlyMaterial:
                neighbors = None
                if is_center:
                    grdBuilder = centerBlk
                else:
                    grdBuilder = self.grdBuilder
                    if sx * sx <= 1 and sy * sy <= 1:
                        neighbors = [(sx, sy, centerBlk, 1)]

                # DEMGridBuilder
                grdBuilder.setup(blockIndex, grid_seg, extent, planeWidth, planeHeight,
                                 offsetX=planeWidth * sx,
                                 offsetY=planeHeight * sy,
                                 roughness=1 if is_center else roughness,
                                 edgeRoughness=roughness if is_center else 1,
                                 clip_geometry=clip_geometry if is_center else None,
                                 neighbors=neighbors)
                yield grdBuilder

            # set up material builder for remaininig materials
            if self.layer.opt.allMaterials:
                for idx in range(1, mtlCount):
                    id = materials[idx].get("id")
                    self.mtlBuilder.setup(blockIndex, extent, id, useNow=bool(id == currentMtlId))
                    yield self.mtlBuilder

            self.progress(i + 1, size2)
