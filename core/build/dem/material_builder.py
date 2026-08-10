# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from .property_reader import DEMPropertyReader
from ..datamanager.material import MaterialManager, MaterialType
from ...const import DEMMtlType
from ....utils.js import hex_color
from ....utils.qt import canSaveAsWebP


class DEMMaterialBuilder:
    """Generates materials for DEM layer."""

    def __init__(self, layer, settings, imageManager, assetDestination):
        self.layer = layer
        self.settings = settings
        self.materialManager = MaterialManager(imageManager, settings.materialType())

        self.assetDestination = assetDestination

        self.mtlId = None

    def setup(self, blockIndex, extent, mtlId=None, asBlock=True, useNow=True):
        self.blockIndex = blockIndex
        self.extent = extent
        self.mtlId = mtlId
        self.asBlock = asBlock
        self.useNow = useNow

    def build(self):
        """
        @returns {DEMMaterialBlockData}
        """
        mtlId = self.mtlId or self.layer.properties.get("mtlId")
        m = self.layer.material(mtlId)
        if m:
            mtlIndex = self.layer.mtlIndex(mtlId)

        else:   # fallback to materials[0]
            m = self.layer.properties.get("materials", [])
            m = m[0] if len(m) else {}
            mtlIndex = 0

        p = m.get("properties", {})
        tex_size = DEMPropertyReader.textureSize(p, self.extent, self.settings)
        opacity = DEMPropertyReader.opacity(p)

        transparent_bg = p.get("checkBox_TransparentBackground", False)
        shading = p.get("checkBox_Shading", True)
        flat = shading and p.get("checkBox_FlatShading", False)

        if p.get("radioButton_WebP") and canSaveAsWebP():
            fmt = "WebP"
        elif p.get("radioButton_PNG"):
            fmt = "PNG"
        else:
            fmt = "JPEG"
            transparent_bg = False

        mtl_type = m.get("type", DEMMtlType.MAPCANVAS)
        match mtl_type:
            case DEMMtlType.MAPCANVAS:
                mi = self.materialManager.getMapImageIndex(
                    tex_size.width(), tex_size.height(), self.extent,
                    opacity, transparent_bg, shading, flat, fmt
                )

            case DEMMtlType.LAYER:
                layerids = p.get("layerIds", [])
                mi = self.materialManager.getLayerImageIndex(
                    layerids, tex_size.width(), tex_size.height(), self.extent,
                    opacity, transparent_bg, shading, flat, fmt
                )

            case DEMMtlType.FILE:
                filepath = p.get("lineEdit_ImageFile", "")
                mi = self.materialManager.getImageFileIndex(
                    filepath,
                    opacity, transparent_bg=True, shading=shading, flat=flat, doubleSide=True
                )

            case _:     # const.MTL_COLOR
                mt = MaterialType.DEFAULT_MESH if shading else MaterialType.MESH_BASIC
                color = hex_color(p.get("colorButton_Color", 0), prefix="0x")

                mi = self.materialManager.getMeshIndex(mt, color, opacity, flat=flat, doubleSide=True)

        # build material
        _mi_str = "_{}".format(mtlIndex) if mtlIndex else ""
        ext = fmt.lower().replace("jpeg", "jpg")
        tail = f"{self.blockIndex}{_mi_str}.{ext}"

        filepath = url = None
        if self.assetDestination:
            filepath = self.assetDestination.path(tail)
            url = self.assetDestination.url(tail)

        d = self.materialManager.build(mi, filepath, url, self.settings.requiresJsonSerializable)
        d["mtlIndex"] = mtlIndex
        d["useNow"] = self.useNow
        if self.asBlock:
            return {
                "type": "block",
                "layer": self.layer.jsLayerId,
                "block": self.blockIndex,
                "materials": [d]
            }
        return d

    def currentMtl(self):
        mtlId = self.mtlId or self.layer.properties.get("mtlId")
        return self.layer.material(mtlId)

    def currentMtlType(self):
        return self.currentMtl().get("type", DEMMtlType.MAPCANVAS)

    def currentMtlProperties(self):
        return self.currentMtl().get("properties", {})
