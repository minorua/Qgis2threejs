# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import os

from qgis.PyQt.QtCore import Qt, QBuffer, QByteArray, QIODevice, QSize
from qgis.PyQt.QtGui import QColor, QImage, QPainter
from qgis.core import Qgis, QgsMapSettings

from .base import DataManager
from ....utils.file import copyFile
from ....utils.js import image2dataUri, imageFile2dataUri
from ....utils.logging import logger
from ....utils.qgis import getLayersByLayerIds


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


def jpegCompressedImage(image):
    """Recreate a QImage compressed as JPEG."""
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPEG")

    return QImage.fromData(ba, "JPEG")
