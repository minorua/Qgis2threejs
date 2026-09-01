# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import os
from typing import NamedTuple

from qgis.PyQt.QtCore import Qt, QBuffer, QByteArray, QIODevice, QRectF, QSize
from qgis.PyQt.QtGui import QColor, QFont, QImage, QPainter
from qgis.core import Qgis, QgsMapSettings

from .base import DataManager
from ...mapextent import MapExtent
from ....utils.file import copyFile
from ....utils.js import image2dataUri, imageFile2dataUri
from ....utils.logging import logger
from ....utils.qgis import getLayersByLayerIds


class ImageSourceType:
    MAP_IMAGE = 1
    LAYER_IMAGE = 2
    IMAGE_FILE = 3


class ImageSource(NamedTuple):
    type: int
    src: list | str | None = None
    width: int | None = None
    height: int | None = None
    extent: MapExtent | None = None
    validExtent: MapExtent | None = None
    transparent_bg: bool = False
    format: str = "PNG"
    debugText: str = ""


class ImageManager(DataManager):

    _list: list[ImageSource]

    def __init__(self, baseMapSettings=None):
        super().__init__()
        self.setBaseMapSettings(baseMapSettings)
        self._renderer = None

    def setBaseMapSettings(self, mapSettings):
        self.baseMapSettings = QgsMapSettings(mapSettings) if mapSettings else QgsMapSettings()

    def getIndex(self, s: ImageSource):
        return self._index(s)

    def _renderImage(self, s: ImageSource):
        from qgis.core import QgsMapRendererCustomPainterJob
        antialias = True

        settings = QgsMapSettings(self.baseMapSettings)
        settings.setOutputSize(QSize(s.width, s.height))
        settings.setExtent(s.extent.unrotatedRect())
        # settings.setRotation(s.extent.rotation())

        if s.src:
            settings.setLayers(getLayersByLayerIds(s.src))

        if s.transparent_bg:
            settings.setBackgroundColor(QColor(Qt.GlobalColor.transparent))

        has_pluginlayer = False
        for layer in settings.layers():
            if layer and layer.type() == Qgis.LayerType.Plugin:
                has_pluginlayer = True
                break

        image = QImage(s.width, s.height, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)

        painter = QPainter()
        painter.begin(image)
        if antialias:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if s.validExtent is not None:
            nx = s.validExtent.width() / s.extent.width()
            ny = s.validExtent.height() / s.extent.height()
            painter.setClipRect(
                QRectF(0, (1 - ny) * s.height, nx * s.width, s.height)
            )

        job = QgsMapRendererCustomPainterJob(settings, painter)
        if has_pluginlayer:
            job.renderSynchronously()   # use this method so that TileLayerPlugin layer is rendered correctly
        else:
            job.start()
            job.waitForFinished()

        if s.debugText:
            font_size = 64
            font_color = QColor(255, 255, 0)

            font = QFont()
            font.setPointSize(font_size)

            painter.setFont(font)
            painter.setPen(font_color)
            painter.drawText(10, s.height - 10, s.debugText)

        painter.end()

        return image

    def image(self, index):
        s = self._list[index]
        if s.type == ImageSourceType.IMAGE_FILE:
            if os.path.isfile(s.src):
                return QImage(s.src)
            else:
                logger.warning(f"Image file not found: {s.src}")
        else:
            image = self._renderImage(s)

            if s.format == "JPEG":
                return jpegCompressedImage(image)

            return image

        image = QImage(1, 1, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.lightGray)
        return image

    def dataUri(self, index):
        s = self._list[index]
        if s.type == ImageSourceType.IMAGE_FILE:
            return imageFile2dataUri(s.src)

        image = self.image(index)
        if image:
            return image2dataUri(image, fmt=s.format)

        return ""

    def write(self, index, path):
        s = self._list[index]
        if s.type == ImageSourceType.IMAGE_FILE:
            if os.path.isfile(s.src):
                copyFile(s.src, path, overwrite=True)
                return

        self.image(index).save(path)


def jpegCompressedImage(image):
    """Recreate a QImage compressed as JPEG."""
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPEG")

    return QImage.fromData(ba, "JPEG")
