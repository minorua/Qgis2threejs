# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import os
from typing import NamedTuple

from qgis.PyQt.QtCore import Qt, QBuffer, QByteArray, QIODevice, QSize, QUrl
from qgis.PyQt.QtGui import QColor, QImage, QPainter
from qgis.core import Qgis, QgsMapSettings

from ..const import ScriptFile
from ..mapextent import MapExtent
from ...utils.file import copyFile
from ...utils.js import base64file, image2dataUri, imageFile2dataUri
from ...utils.logging import logger
from ...utils.qgis import getLayersByLayerIds


class DataManager:
    """ manages a list of unique items """

    def __init__(self):
        self._list = []

    def count(self):
        return len(self._list)

    def _index(self, data):
        if data in self._list:
            return self._list.index(data)

        index = len(self._list)
        self._list.append(data)
        return index


class ImageManager(DataManager):

    IMG_MAP = 1
    IMG_LAYER = 2
    IMG_FILE = 3

    def __init__(self, baseMapSettings=None):
        super().__init__()
        self.setBaseMapSettings(baseMapSettings)
        self._renderer = None

    def setBaseMapSettings(self, mapSettings):
        self.baseMapSettings = QgsMapSettings(mapSettings) if mapSettings else QgsMapSettings()

    def mapImageIndex(self, width, height, extent, transparent_bg, format):
        img = (self.IMG_MAP, (None, width, height, extent, transparent_bg), format)
        return self._index(img)

    def layerImageIndex(self, layerids, width, height, extent, transparent_bg, format):
        img = (self.IMG_LAYER, (layerids, width, height, extent, transparent_bg), format)
        return self._index(img)

    def imageFileIndex(self, path):
        img = (self.IMG_FILE, path, "")
        return self._index(img)

    def _renderImage(self, layerids, width, height, extent, transparent_bg=False):
        # render layers with QgsMapRendererCustomPainterJob
        from qgis.core import QgsMapRendererCustomPainterJob
        antialias = True

        settings = QgsMapSettings(self.baseMapSettings)
        settings.setOutputSize(QSize(width, height))
        settings.setExtent(extent.unrotatedRect())
        settings.setRotation(extent.rotation())

        if layerids:
            settings.setLayers(getLayersByLayerIds(layerids))

        if transparent_bg:
            settings.setBackgroundColor(QColor(Qt.GlobalColor.transparent))

        has_pluginlayer = False
        for layer in settings.layers():
            if layer and layer.type() == Qgis.LayerType.Plugin:
                has_pluginlayer = True
                break

        # create an image
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter()
        painter.begin(image)
        if antialias:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # rendering
        job = QgsMapRendererCustomPainterJob(settings, painter)
        if has_pluginlayer:
            job.renderSynchronously()   # use this method so that TileLayerPlugin layer is rendered correctly
        else:
            job.start()
            job.waitForFinished()
        painter.end()

        return image

    def image(self, index):
        imageType, args, fmt = self._list[index]

        if imageType == self.IMG_FILE:
            image_path = args
            if os.path.isfile(image_path):
                return QImage(image_path)
            else:
                logger.warning("Image file not found: {0}".format(image_path))

        else:   # IMG_MAP or IMG_LAYER
            image = self._renderImage(*args)

            if fmt == "JPEG":
                return jpegCompressedImage(image)

            return image

        image = QImage(1, 1, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.lightGray)
        return image

    def dataUri(self, index):
        imageType, args, fmt = self._list[index]

        if imageType == self.IMG_FILE:
            return imageFile2dataUri(args)

        image = self.image(index)
        if image:
            return image2dataUri(image, fmt=fmt)

        return ""

    def write(self, index, path):
        imageType, args, _fmt = self._list[index]

        if imageType == self.IMG_FILE:
            image_path = args
            if os.path.isfile(image_path):
                copyFile(image_path, path, overwrite=True)
                return

        self.image(index).save(path)


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


class ModelManager(DataManager):

    def __init__(self, exportSettings):
        super().__init__()
        self.exportSettings = exportSettings

    def modelIndex(self, path):
        return self._index(path)

    def build(self, export=True, base64=False):
        a = []
        for path_url in self._list:
            if path_url.startswith("http:") or path_url.startswith("https:"):
                a.append({"url": path_url})

            elif base64:
                _, ext = os.path.splitext(path_url)
                a.append({"base64": base64file(path_url),
                          "ext": ext[1:],
                          "resourcePath": "./data/{}/models/".format(self.exportSettings.outputFileTitle())})
            else:
                if export:
                    url = "./data/{}/models/{}".format(self.exportSettings.outputFileTitle(),
                                                       os.path.basename(path_url))
                else:
                    url = QUrl.fromLocalFile(path_url).toString()

                a.append({"url": url})
        return a

    def hasColladaModel(self):
        for f in self._list:
            _, ext = os.path.splitext(f)
            if ext == ".dae":
                return True
        return False

    def hasGLTFModel(self):
        for f in self._list:
            _, ext = os.path.splitext(f)
            if ext in [".gltf", ".glb"]:
                return True
        return False

    def filesToCopy(self):
        THREE = "web/js/lib/three"
        LOADER = THREE + "/loaders"
        UTILS = THREE + "/utils"

        f = []
        if self._list:
            if self.hasColladaModel():
                f.append({
                    "files": [
                        LOADER + "/ColladaLoader.js",
                        LOADER + "/TGALoader.js"
                    ],
                    "dirs": [
                        LOADER + "/collada"
                    ],
                    "dest": "three/loaders"
                })

            if self.hasGLTFModel():
                f.append({
                    "files": [
                        LOADER + "/GLTFLoader.js"
                    ],
                    "dest": "three/loaders"
                })
                f.append({
                    "files": [
                        UTILS + "/BufferGeometryUtils.js",
                        UTILS + "/SkeletonUtils.js"
                    ],
                    "dest": "three/utils"
                })

            f.append({"files": self._list, "dest": "./data/{}/models".format(self.exportSettings.outputFileTitle())})
        return f

    def moduleFiles(self):
        files = []
        if self._list:
            if self.hasColladaModel():
                files.append(("./three/loaders/ColladaLoader.js", ScriptFile.TYPE_CLASS))

            if self.hasGLTFModel():
                files.append(("./three/loaders/GLTFLoader.js", ScriptFile.TYPE_CLASS))

        return files


def jpegCompressedImage(image):
    """Recreate a QImage compressed as JPEG."""
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPEG")

    return QImage.fromData(ba, "JPEG")
