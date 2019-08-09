# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
        begin                : 2014-01-16
        copyright            : (C) 2014 Minoru Akagi
        email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os

from PyQt5.QtCore import Qt, QSize, QUrl
from PyQt5.QtGui import QColor, QImage, QPainter
from qgis.core import QgsMapLayer

from . import qgis2threejstools as tools
from .qgis2threejstools import logMessage


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

    IMAGE_FILE = 1
    CANVAS_IMAGE = 2
    MAP_IMAGE = 3
    LAYER_IMAGE = 4

    def __init__(self, exportSettings):
        DataManager.__init__(self)
        self.exportSettings = exportSettings
        self._renderer = None

    def imageIndex(self, path):
        img = (self.IMAGE_FILE, path)
        return self._index(img)

    def canvasImageIndex(self, transp_background):
        img = (self.CANVAS_IMAGE, transp_background)
        return self._index(img)

    def mapImageIndex(self, width, height, extent, transp_background):
        img = (self.MAP_IMAGE, (width, height, extent, transp_background))
        return self._index(img)

    def layerImageIndex(self, layerids, width, height, extent, transp_background):
        img = (self.LAYER_IMAGE, (layerids, width, height, extent, transp_background))
        return self._index(img)

    def mapCanvasImage(self, transp_background=False):
        """ returns base64 encoded map canvas image """
        canvas = self.exportSettings.canvas
        size = self.exportSettings.mapSettings.outputSize()
        if canvas is None or transp_background or True:   #
            return self.renderedImage(size.width(), size.height(), self.exportSettings.baseExtent, transp_background)

        # bad - incompletely rendered image is given
        image = QImage(size.width(), size.height(), QImage.Format_ARGB32_Premultiplied)
        painter = QPainter()
        painter.begin(image)
        canvas.render(painter)
        painter.end()
        return image

    def renderedImage(self, width, height, extent, transp_background=False, layerids=None):
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
            settings.setLayers(tools.getLayersByLayerIds(layerids))

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
        image = self._list[index]
        imageType = image[0]
        if imageType == self.IMAGE_FILE:
            image_path = image[1]
            if os.path.isfile(image_path):
                return QImage(image_path)
            else:
                logMessage("Image file not found: {0}".format(image_path))
                image = QImage(1, 1, QImage.Format_RGB32)
                image.fill(Qt.lightGray)
                return image

        if imageType == self.MAP_IMAGE:
            width, height, extent, transp_background = image[1]
            return self.renderedImage(width, height, extent, transp_background)

        if imageType == self.LAYER_IMAGE:
            layerids, width, height, extent, transp_background = image[1]
            return self.renderedImage(width, height, extent, transp_background, layerids)

        # imageType == self.CANVAS_IMAGE:
        transp_background = image[1]
        return self.mapCanvasImage(transp_background)

    def base64image(self, index):
        image = self.image(index)
        if image:
            return tools.base64image(image)
        return None

    def write(self, index, path):
        self.image(index).save(path)

    def writeAll(self, pathRoot):
        for i in range(self.count()):
            self.image(i).save("{0}{1}.png".format(pathRoot, i))


class MaterialManager(DataManager):

    # following six material types are defined also in JS
    # first three types are basic material types
    MESH_LAMBERT = 0
    MESH_PHONG = 1
    MESH_TOON = 2

    LINE_BASIC = 3
    LINE_DASHED = 4
    SPRITE_IMAGE = 5
    POINT = 6

    # other material types for internal use
    MESH_MATERIAL = 10
    MESH_FLAT = 11
    WIREFRAME = 12

    CANVAS_IMAGE = 20
    MAP_IMAGE = 21
    LAYER_IMAGE = 22
    IMAGE_FILE = 23

    ERROR_COLOR = "0"

    def __init__(self, basicType=MESH_LAMBERT):
        DataManager.__init__(self)

        self.basicMaterialType = basicType

    def _indexCol(self, type, color, opacity=1, doubleSide=False, opts=None):
        if color[0:2] != "0x":
            color = self.ERROR_COLOR
        mtl = (type, color, opacity, doubleSide, opts)
        return self._index(mtl)

    def getMeshMaterialIndex(self, color, opacity=1, doubleSide=False):
        return self._indexCol(self.MESH_MATERIAL, color, opacity, doubleSide)

    def getFlatMeshMaterialIndex(self, color, opacity=1, doubleSide=False):
        return self._indexCol(self.MESH_FLAT, color, opacity, doubleSide)

    def getPointMaterialIndex(self, color, opacity=1, size=1):
        return self._indexCol(self.POINT, color, opacity, False, size)

    def getBasicLineIndex(self, color, opacity=1):
        return self._indexCol(self.LINE_BASIC, color, opacity)

    def getDashedLineIndex(self, color, opacity=1):
        return self._indexCol(self.LINE_DASHED, color, opacity)

    def getWireframeIndex(self, color, opacity=1):
        return self._indexCol(self.WIREFRAME, color, opacity)

    def getCanvasImageIndex(self, opacity=1, transp_background=False):
        mtl = (self.CANVAS_IMAGE, None, opacity, True, transp_background)
        return self._index(mtl)

    def getMapImageIndex(self, width, height, extent, opacity=1, transp_background=False):
        mtl = (self.MAP_IMAGE, None, opacity, True, (width, height, extent, transp_background))
        return self._index(mtl)

    def getLayerImageIndex(self, layerids, width, height, extent, opacity=1, transp_background=False):
        mtl = (self.LAYER_IMAGE, None, opacity, True, (layerids, width, height, extent, transp_background))
        return self._index(mtl)

    def getImageFileIndex(self, path, opacity=1, transp_background=False, doubleSide=False):
        mtl = (self.IMAGE_FILE, None, opacity, doubleSide, (path, transp_background))
        return self._index(mtl)

    def getSpriteImageIndex(self, path_url, opacity=1):
        transp_background = True
        mtl = (self.SPRITE_IMAGE, None, opacity, False, (path_url, transp_background))
        return self._index(mtl)

    def build(self, index, imageManager, filepath=None, url=None, base64=False):

        mt, color, opacity, doubleSide, opts = self._list[index]
        transp_background = False

        m = {
            "type": mt if mt in [self.POINT, self.LINE_BASIC, self.LINE_DASHED, self.SPRITE_IMAGE] else self.basicMaterialType
        }

        if color is None:
            if mt == self.CANVAS_IMAGE:
                transp_background = opts
                imgIndex = imageManager.canvasImageIndex(transp_background)
            elif mt == self.MAP_IMAGE:
                width, height, extent, transp_background = opts
                imgIndex = imageManager.mapImageIndex(width, height, extent, transp_background)
            elif mt == self.LAYER_IMAGE:
                layerids, width, height, extent, transp_background = opts
                imgIndex = imageManager.layerImageIndex(layerids, width, height, extent, transp_background)
            elif mt == self.IMAGE_FILE:
                imagepath, transp_background = opts
                imgIndex = imageManager.imageIndex(imagepath)
            elif mt == self.SPRITE_IMAGE:
                path_url, transp_background = opts
                if path_url.startswith("http:") or path_url.startswith("https:"):
                    url = path_url
                    filepath = None
                else:
                    imgIndex = imageManager.imageIndex(path_url)

            if url is None:
                if base64:
                    m["image"] = {"base64": imageManager.base64image(imgIndex)}
                else:
                    m["image"] = {"object": imageManager.image(imgIndex)}
            else:
                m["image"] = {"url": url}

                if filepath:
                    # write image to a file
                    imageManager.write(imgIndex, filepath)
        else:
            m["c"] = int(color, 16)

            if mt == self.POINT:
                m["s"] = opts   # size

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

        return m

    def buildAll(self, imageManager, pathRoot=None, urlRoot=None, base64=False):
        mList = []
        for i in range(len(self._list)):
            if pathRoot is None:
                filepath = url = None
            else:
                filepath = "{0}{1}.png".format(pathRoot, i)
                url = "{0}{1}.png".format(urlRoot, i)
            mList.append(self.build(i, imageManager, filepath, url, base64))
        return mList


class ModelManager(DataManager):

    def __init__(self, exportSettings):
        DataManager.__init__(self)
        self.exportSettings = exportSettings

    def modelIndex(self, path):
        return self._index(path)

    def build(self, export=True):
        l = []
        for path_url in self._list:
            if path_url.startswith("http:") or path_url.startswith("https:"):
                url = path_url
            elif export:
                url = "./data/{}/models/{}".format(self.exportSettings.outputFileTitle(),
                                                   os.path.basename(path_url))
            else:
                url = QUrl.fromLocalFile(path_url).toString()

            l.append({"url": url})
        return l

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
