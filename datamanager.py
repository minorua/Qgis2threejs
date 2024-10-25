# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import os

from PyQt5.QtCore import Qt, QSize, QUrl
from PyQt5.QtGui import QColor, QImage, QPainter
from qgis.core import QgsMapLayer

from . import utils
from .utils import logMessage


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

    def __init__(self, exportSettings):
        DataManager.__init__(self)
        self.exportSettings = exportSettings
        self._renderer = None

    def mapImageIndex(self, width, height, extent, transp_background, format):
        img = (self.IMG_MAP, (None, width, height, extent, transp_background), format)
        return self._index(img)

    def layerImageIndex(self, layerids, width, height, extent, transp_background, format):
        img = (self.IMG_LAYER, (layerids, width, height, extent, transp_background), format)
        return self._index(img)

    def imageFileIndex(self, path):
        img = (self.IMG_FILE, path, "")
        return self._index(img)

    def renderedImage(self, layerids, width, height, extent, transp_background=False):
        # render layers with QgsMapRendererCustomPainterJob
        from qgis.core import QgsMapRendererCustomPainterJob
        antialias = True
        settings = self.exportSettings.mapSettings

        # store old map settings
        old_outputSize = settings.outputSize()
        old_extent = settings.extent()
        old_rotation = settings.rotation()
        old_layers = settings.layers()
        old_backgroundColor = settings.backgroundColor()

        # map settings
        settings.setOutputSize(QSize(width, height))
        settings.setExtent(extent.unrotatedRect())
        settings.setRotation(extent.rotation())

        if layerids:
            settings.setLayers(utils.getLayersByLayerIds(layerids))

        if transp_background:
            settings.setBackgroundColor(QColor(Qt.transparent))

        has_pluginlayer = False
        for layer in settings.layers():
            if layer and layer.type() == QgsMapLayer.PluginLayer:
                has_pluginlayer = True
                break

        # create an image
        image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        painter = QPainter()
        painter.begin(image)
        if antialias:
            painter.setRenderHint(QPainter.Antialiasing)

        # rendering
        job = QgsMapRendererCustomPainterJob(settings, painter)
        if has_pluginlayer:
            job.renderSynchronously()   # use this method so that TileLayerPlugin layer is rendered correctly
        else:
            job.start()
            job.waitForFinished()
        painter.end()

        # restore map settings
        settings.setOutputSize(old_outputSize)
        settings.setExtent(old_extent)
        settings.setRotation(old_rotation)
        settings.setLayers(old_layers)
        settings.setBackgroundColor(old_backgroundColor)

        return image

    def image(self, index):
        imageType, args, fmt = self._list[index]

        if imageType == self.IMG_FILE:
            image_path = args
            if os.path.isfile(image_path):
                return QImage(image_path)
            else:
                logMessage("Image file not found: {0}".format(image_path), warning=True)

        else:   # IMG_MAP or IMG_LAYER
            image = self.renderedImage(*args)

            if fmt == "JPEG":
                return utils.jpegCompressedImage(image)

            return image

        image = QImage(1, 1, QImage.Format_RGB32)
        image.fill(Qt.lightGray)
        return image

    def dataUri(self, index):
        imageType, args, fmt = self._list[index]

        if imageType == self.IMG_FILE:
            return utils.imageFile2dataUri(args)

        image = self.image(index)
        if image:
            return utils.image2dataUri(image, fmt=fmt)

        return ""

    def write(self, index, path):
        imageType, args, fmt = self._list[index]

        if imageType == self.IMG_FILE:
            image_path = args
            if os.path.isfile(image_path):
                utils.copyFile(image_path, path, overwrite=True)
                return

        self.image(index).save(path)


class MaterialManager(DataManager):

    # following six material types are defined also in JS
    # first three types are basic material types
    MESH_LAMBERT = 0
    MESH_PHONG = 1
    MESH_TOON = 2

    LINE = 3
    LINE_MESH = 4
    SPRITE_IMAGE = 5
    POINT = 6

    # other material types for internal use
    MESH_MATERIAL = 10
    MESH_FLAT = 11
    MESH_BASIC = 13
    WIREFRAME = 12

    MAP_IMAGE = 21
    LAYER_IMAGE = 22
    IMAGE_FILE = 23

    ERROR_COLOR = "0"

    def __init__(self, imageManager, basicType=MESH_LAMBERT):
        DataManager.__init__(self)

        self.imageManager = imageManager
        self.basicMaterialType = basicType

    def _indexCol(self, type, color, opacity=1, doubleSide=False, opts=None):
        if color[0:2] != "0x":
            color = self.ERROR_COLOR
        mtl = (type, color, opacity, doubleSide, opts)
        return self._index(mtl)

    def getMeshMaterialIndex(self, color, opacity=1, doubleSide=False):
        return self._indexCol(self.MESH_MATERIAL, color, opacity, doubleSide)

    def getMeshFlatMaterialIndex(self, color, opacity=1, doubleSide=False):
        return self._indexCol(self.MESH_FLAT, color, opacity, doubleSide)

    def getMeshBasicMaterialIndex(self, color, opacity=1, doubleSide=False):
        return self._indexCol(self.MESH_BASIC, color, opacity, doubleSide)

    def getPointMaterialIndex(self, color, opacity=1, size=1):
        return self._indexCol(self.POINT, color, opacity, False, size)

    def getLineIndex(self, color, opacity=1, dashed=False):
        return self._indexCol(self.LINE, color, opacity, opts=dashed)

    def getMeshLineIndex(self, color, opacity=1, thickness=1, dashed=False):
        return self._indexCol(self.LINE_MESH, color, opacity, opts=(thickness, dashed))

    def getWireframeIndex(self, color, opacity=1):
        return self._indexCol(self.WIREFRAME, color, opacity)

    def getMapImageIndex(self, width, height, extent, opacity=1, transp_background=False, shading=True, format="PNG"):
        mtl = (self.MAP_IMAGE, None, opacity, True, ((width, height, extent, transp_background, format), shading))
        return self._index(mtl)

    def getLayerImageIndex(self, layerids, width, height, extent, opacity=1, transp_background=False, shading=True, format="PNG"):
        mtl = (self.LAYER_IMAGE, None, opacity, True, ((layerids, width, height, extent, transp_background, format), shading))
        return self._index(mtl)

    def getImageFileIndex(self, path, opacity=1, transp_background=False, doubleSide=False, shading=True):
        mtl = (self.IMAGE_FILE, None, opacity, doubleSide, (path, transp_background, shading))
        return self._index(mtl)

    def getSpriteImageIndex(self, path_url, opacity=1):
        transp_background = True
        mtl = (self.SPRITE_IMAGE, None, opacity, False, (path_url, transp_background))
        return self._index(mtl)

    def build(self, index, filepath=None, url=None, base64=False):

        mt, color, opacity, doubleSide, opts = self._list[index]
        transp_background = False
        shading = True

        m = {
            "type": mt if mt in [self.POINT, self.LINE, self.LINE_MESH, self.SPRITE_IMAGE] else self.basicMaterialType
        }

        if color is None:
            if mt == self.MAP_IMAGE:
                args, shading = opts
                imgIndex = self.imageManager.mapImageIndex(*args)

            elif mt == self.LAYER_IMAGE:
                args, shading = opts
                imgIndex = self.imageManager.layerImageIndex(*args)

            elif mt == self.IMAGE_FILE:
                imagepath, transp_background, shading = opts
                imgIndex = self.imageManager.imageFileIndex(imagepath)

            elif mt == self.SPRITE_IMAGE:
                path_url, transp_background = opts
                if path_url.startswith("http:") or path_url.startswith("https:"):
                    url = path_url
                    filepath = None
                else:
                    imgIndex = self.imageManager.imageFileIndex(path_url)

            if url is None:
                if base64:
                    m["image"] = {"base64": self.imageManager.dataUri(imgIndex)}
                else:
                    m["image"] = {"object": self.imageManager.image(imgIndex)}
            else:
                m["image"] = {"url": url}

                if filepath:
                    # write image to a file
                    self.imageManager.write(imgIndex, filepath)
        else:
            m["c"] = int(color, 16)

            if mt == self.POINT:
                m["s"] = opts   # size

            elif mt == self.LINE:
                m["dashed"] = opts

            elif mt == self.LINE_MESH:
                thickness, dashed = opts
                m["thickness"] = thickness
                m["dashed"] = dashed

            elif mt == self.MESH_BASIC:
                shading = False

        if transp_background:
            m["t"] = 1

        if mt == self.WIREFRAME:
            m["w"] = 1

        if mt == self.MESH_FLAT:
            m["flat"] = 1

        if opacity < 1:
            m["o"] = opacity

        if doubleSide:
            m["ds"] = 1

        if not shading:
            m["bm"] = True

        return m

    def buildAll(self, pathRoot=None, urlRoot=None, base64=False):
        mList = []
        for i, item in enumerate(self._list):
            mt, color, opacity, doubleSide, opts = item
            filepath = url = None

            if pathRoot and color is None:
                if mt == self.SPRITE_IMAGE:
                    path_url = opts[0]
                    if not path_url.startswith("http:") and not path_url.startswith("https:"):
                        ext = os.path.splitext(path_url)[1].lower()
                        suffix = "{}{}".format(i, ext)
                        filepath = pathRoot + suffix
                        url = urlRoot + suffix

            m = self.build(i, filepath, url, base64)
            mList.append(m)
        return mList


class ModelManager(DataManager):

    def __init__(self, exportSettings):
        DataManager.__init__(self)
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
                a.append({"base64": utils.base64file(path_url),
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
        f = []
        if self._list:
            if self.hasColladaModel():
                f.append({"files": ["js/threejs/loaders/ColladaLoader.js"], "dest": "threejs/loaders"})
            if self.hasGLTFModel():
                f.append({"files": ["js/threejs/loaders/GLTFLoader.js"], "dest": "threejs/loaders"})
            f.append({"files": self._list, "dest": "./data/{}/models".format(self.exportSettings.outputFileTitle())})
        return f

    def scripts(self):
        s = []
        if self._list:
            if self.hasColladaModel():
                s.append("./threejs/loaders/ColladaLoader.js")
            if self.hasGLTFModel():
                s.append("./threejs/loaders/GLTFLoader.js")
        return s
