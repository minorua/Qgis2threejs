# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

from threading import Lock

from qgis.core import Qgis, QgsApplication
from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot

from ..const import LayerType
from ..exportsettings import ExportSettings, Layer
from .datamanager import ImageManager
from .dem.builder import DEMLayerBuilder
from .vector.builder import VectorLayerBuilder
from .pointcloud.builder import PointCloudLayerBuilder
from ...utils import int_color, noop, logger


LayerBuilderFactory = {
    LayerType.DEM: DEMLayerBuilder,
    LayerType.POINT: VectorLayerBuilder,
    LayerType.LINESTRING: VectorLayerBuilder,
    LayerType.POLYGON: VectorLayerBuilder,
    LayerType.POINTCLOUD: PointCloudLayerBuilder
}


class ThreeJSBuilder(QObject):

    # signals - builder to controller interface
    dataReady = pyqtSignal(dict)
    taskCompleted = pyqtSignal()
    taskAborted = pyqtSignal()
    progressUpdated = pyqtSignal(int, int, str)       # current, total, msg

    readyToQuit = pyqtSignal()

    def __init__(self, parent, progress=None, log=None, isInUiThread=True):
        super().__init__(parent)

        self.progress = progress or self._progress
        self.log = log or noop

        self._aborted = False
        self._isInUiThread = isInUiThread
        self._lock = Lock()

    def _progress(self, current, total=100, msg=""):
        self.progressUpdated.emit(current, total, msg)

    @property
    def aborted(self):
        if self._isInUiThread:
            QgsApplication.processEvents()
            return self._aborted

        with self._lock:
            return self._aborted

    @aborted.setter
    def aborted(self, value):
        with self._lock:
            if self._aborted != value:
                self._aborted = value
                logger.debug(f"ThreeJSBuilder: aborted={self._aborted}.")

    def abort(self):
        self.aborted = True

    @pyqtSlot()
    def quit(self):
        # break circular references
        self.progress = noop

        # move to the main thread
        self.moveToThread(QgsApplication.instance().thread())
        self.readyToQuit.emit()

    @pyqtSlot(ExportSettings)
    def buildSceneSlot(self, settings):
        self.aborted = False
        self.progress(0, msg="Building scene...")

        data = self.buildScene(settings, build_layers=False)
        if data:
            self.dataReady.emit(data)

        self.taskCompleted.emit()

    @pyqtSlot(Layer, ExportSettings)
    def buildLayerSlot(self, layer, settings):
        self.aborted = False
        self.progress(0, msg=f"Building {layer.name} layer...")

        layerBuilder = self._layerBuilder(layer, settings, progress=self._progress)
        data = layerBuilder.build()
        if data:
            self.dataReady.emit(data)

        for blockBuilder in layerBuilder.blockBuilders():
            logger.debug("Building a block.")

            if self.aborted:
                self.taskAborted.emit()
                return

            data = blockBuilder.build()
            if data:
                self.dataReady.emit(data)

        self.taskCompleted.emit()

    def buildScene(self, settings, build_layers=True):
        self.aborted = False

        obj = self._buildScene(settings)
        if build_layers:
            obj["layers"] = self._buildLayers(settings)
        return obj

    def _buildScene(self, settings):
        self.progress(0, msg="Building scene...")
        be = settings.baseExtent()
        mapTo3d = settings.mapTo3d()

        p = {
            "baseExtent": {
                "cx": be.center().x(),
                "cy": be.center().y(),
                "width": be.width(),
                "height": be.height(),
                "rotation": be.rotation()
            },
            "origin": {
                "x": mapTo3d.origin.x(),
                "y": mapTo3d.origin.y(),
                "z": mapTo3d.origin.z()
            },
            "zScale": mapTo3d.zScale
        }

        sp = settings.sceneProperties()
        p["light"] = "point" if sp.get("radioButton_PtLight") else "directional"

        if sp.get("groupBox_Fog"):
            d = sp["slider_Fog"]
            p["fog"] = {
                "color": int_color(sp["colorButton_Fog"]),
                "density": (d * d + 0.2) * 0.0002 / be.width()
            }

        if settings.needsProjString():
            crs = settings.crs
            p["proj"] = crs.toProj4() if Qgis.QGIS_VERSION_INT < 31003 else crs.toProj()

        self.log("Z scale: {}".format(mapTo3d.zScale))

        obj = {
            "type": "scene",
            "properties": p
        }
        return obj

    def _buildLayers(self, settings):
        layers = []
        layer_list = [layer for layer in settings.layers() if layer.visible]
        total = len(layer_list)
        for i, layer in enumerate(layer_list):
            if self.aborted:
                break

            self.progress(i, total, f"Building {layer.name} layer...")
            obj = self._buildLayer(layer, settings)
            if obj:
                layers.append(obj)

        if self.aborted:
            return None

        return layers

    def _buildLayer(self, layer, settings):
        layerBuilder = self._layerBuilder(layer, settings)

        obj = layerBuilder.build(build_blocks=False)

        blocks = []
        for blockBuilder in layerBuilder.blockBuilders():
            if self.aborted:
                return None

            blocks.append(blockBuilder.build())

        if blocks:
            body = obj.get("body", {})
            body["blocks"] = blocks
            obj["body"] = body

        return obj

    def _layerBuilder(self, layer, settings, progress=None):
        imageManager = ImageManager(settings.mapSettings)
        return LayerBuilderFactory.get(layer.type, VectorLayerBuilder)(layer, settings, imageManager, progress=progress)
