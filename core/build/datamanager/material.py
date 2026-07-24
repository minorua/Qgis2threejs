# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import os
from typing import NamedTuple

from .base import DataManager
from .image import ImageManager
from ...mapextent import MapExtent
from ....utils.logging import logger


class MaterialType:
    MESH_LAMBERT = 0
    MESH_PHONG = 1
    MESH_TOON = 2
    MESH_BASIC = 3

    LINE = 10
    LINE_MESH = 11
    SPRITE_IMAGE = 12
    POINT = 13

    DEFAULT_MESH = 20


class TextureType:
    MAP_IMAGE = 1
    LAYER_IMAGE = 2
    IMAGE_FILE = 3


class Texture(NamedTuple):
    type: int
    src: list | str | None = None
    width: int | None = None
    height: int | None = None
    extent: MapExtent | None = None
    transparent_bg: bool = False
    format: str = "PNG"


class Material(NamedTuple):
    type: int
    color: str = ""
    opacity: float = 1.0
    doubleSide: bool = False
    flat: bool = False
    options: tuple | Texture | None = None



class MaterialManager(DataManager):

    ERROR_COLOR = "0"

    def __init__(self, imageManager: ImageManager, defaultMaterialType=MaterialType.MESH_LAMBERT):
        super().__init__()
        self.imageManager = imageManager
        self.defaultMaterialType = defaultMaterialType

    def _indexCol(self, mtl: Material):
        if mtl.color[0:2] != "0x":
            logger.warning(f"Invalid color value: {mtl.color}")
            mtl = mtl._replace(color=self.ERROR_COLOR)

        return self._index(mtl)

    def getMeshIndex(self, type=MaterialType.DEFAULT_MESH, color="", opacity=1.0, doubleSide=False, flat=False, options: tuple | Texture | None = None):
        return self._indexCol(Material(type, color, opacity, doubleSide, flat, options))

    def getLineIndex(self, color, opacity=1, dashed=False):
        return self._indexCol(Material(MaterialType.LINE, color, opacity, options=(dashed,)))

    def getMeshLineIndex(self, color, opacity=1, thickness=1, dashed=False):
        return self._indexCol(Material(MaterialType.LINE_MESH, color, opacity, options=(thickness, dashed)))

    def _indexTex(self, texture, opacity, shading, doubleSide=True):
        m = Material(MaterialType.DEFAULT_MESH if shading else MaterialType.MESH_BASIC, opacity=opacity, doubleSide=doubleSide, options=texture)
        return self._index(m)

    def getMapImageIndex(self, width, height, extent, opacity=1, transparent_bg=False, shading=True, format="PNG"):      # TODO: order
        tex = Texture(TextureType.MAP_IMAGE, None, width, height, extent, transparent_bg, format)
        return self._indexTex(tex, opacity, shading)

    def getLayerImageIndex(self, layerids, width, height, extent, opacity=1, transparent_bg=False, shading=True, format="PNG"):
        tex = Texture(TextureType.LAYER_IMAGE, layerids, width, height, extent, transparent_bg, format)
        return self._indexTex(tex, opacity, shading)

    def getImageFileIndex(self, path, opacity=1, transparent_bg=False, doubleSide=False, shading=True):
        tex = Texture(TextureType.IMAGE_FILE, src=path, transparent_bg=transparent_bg)
        return self._indexTex(tex, opacity, shading, doubleSide)

    def getSpriteImageIndex(self, path_url, opacity=1):
        tex = Texture(TextureType.IMAGE_FILE, src=path_url, transparent_bg=True)
        m = Material(MaterialType.SPRITE_IMAGE, opacity=opacity, options=tex)
        return self._index(m)

    def build(self, index, filepath=None, url=None, base64=False):
        mtl: Material = self._list[index]

        m = {
            "type": self.defaultMaterialType if mtl.type == MaterialType.DEFAULT_MESH else mtl.type
        }

        if isinstance(mtl.options, Texture):
            tex = mtl.options
            match tex.type:
                case TextureType.MAP_IMAGE:
                    imgIndex = self.imageManager.mapImageIndex(tex.width, tex.height, tex.extent, tex.transparent_bg, tex.format)

                case TextureType.LAYER_IMAGE:
                    imgIndex = self.imageManager.layerImageIndex(tex.src, tex.width, tex.height, tex.extent, tex.transparent_bg, tex.format)

                case TextureType.IMAGE_FILE:
                    if mtl.type == MaterialType.SPRITE_IMAGE:
                        path_url = tex.src
                        if path_url.startswith("http:") or path_url.startswith("https:"):
                            url = path_url
                            filepath = None
                        else:
                            imgIndex = self.imageManager.imageFileIndex(path_url)
                    else:
                        imgIndex = self.imageManager.imageFileIndex(tex.src)

            if url is None:
                m["image"] = {"base64": self.imageManager.dataUri(imgIndex)}
            else:
                m["image"] = {"url": url}

                if filepath:
                    self.imageManager.write(imgIndex, filepath)

            if tex.transparent_bg:
                m["t"] = 1

        else:
            m["c"] = int(mtl.color, 16)

            match mtl.type:
                case MaterialType.POINT:
                    size = mtl.options[0]
                    m["s"] = size

                case MaterialType.LINE:
                    dashed = mtl.options[0]
                    m["dashed"] = dashed

                case MaterialType.LINE_MESH:
                    thickness, dashed = mtl.options
                    m["thickness"] = thickness
                    m["dashed"] = dashed

        if mtl.opacity < 1:
            m["o"] = mtl.opacity

        if mtl.flat:
            m["flat"] = 1

        if mtl.doubleSide:
            m["ds"] = 1

        return m

    def buildAll(self, pathRoot=None, urlRoot=None, base64=False):
        mList = []
        for i, mtl in enumerate(self._list):
            filepath = url = None

            if pathRoot and mtl.type == MaterialType.SPRITE_IMAGE:
                tex = mtl.options
                path_url = tex.src
                if not path_url.startswith("http:") and not path_url.startswith("https:"):
                    ext = os.path.splitext(path_url)[1].lower()
                    suffix = f"{i}{ext}"
                    filepath = pathRoot + suffix
                    url = urlRoot + suffix

            m = self.build(i, filepath, url, base64)
            mList.append(m)
        return mList
