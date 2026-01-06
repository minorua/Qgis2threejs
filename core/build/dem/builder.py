# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import QSize
from qgis.core import QgsPoint, QgsProject

from .grid_builder import DEMGridBuilder
from .material_builder import DEMMaterialBuilder
from .property_reader import DEMPropertyReader
from ..layerbuilderbase import LayerBuilderBase
from ...const import DEMMtlType
from ...geometry import dissolvePolygonsWithinExtent
from ...mapextent import MapExtent
from ....conf import DEBUG_MODE


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
        self.grdBuilder = DEMGridBuilder(self.settings, self.mtlBuilder.materialManager, self.layer, self.provider, self.pathRoot, self.urlRoot)

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

    def blockCount(self):
        tiles = self.properties.get("checkBox_Tiles", False)
        size = self.properties.get("spinBox_Size", 1) if tiles else 1
        return size * size

    def layerProperties(self):
        """Return layer properties specific to this DEM layer."""
        p = LayerBuilderBase.layerProperties(self)
        p["type"] = "dem"
        p["clipped"] = self.properties.get("checkBox_Clip", False)
        p["mtlNames"] = [mtl.get("name", "") for mtl in self.properties.get("materials", [])]
        p["mtlIdx"] = self.layer.mtlIndex(self.properties.get("mtlId"))
        return p

    def blockBuilders(self):
        """Yield builders that produce DEM tiles and materials."""
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
        clip_option = self.properties.get("checkBox_Clip", False)
        if clip_option:
            clip_layerId = self.properties.get("comboBox_ClipLayer")
            clip_layer = QgsProject.instance().mapLayer(clip_layerId) if clip_layerId else None
            if clip_layer:
                clip_geometry = dissolvePolygonsWithinExtent(clip_layer, be, self.settings.crs)

        # tiles (old name: surrounding blocks)
        tiles = self.properties.get("checkBox_Tiles", False)
        roughness = self.properties.get("spinBox_Roughening", 1) if tiles else 1
        size = self.properties.get("spinBox_Size", 1) if tiles else 1
        size2 = size * size

        centerBlk = DEMGridBuilder(self.settings, self.mtlBuilder.materialManager, self.layer, self.provider, self.pathRoot, self.urlRoot)
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
