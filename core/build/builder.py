# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

from threading import Lock

from qgis.core import Qgis, QgsApplication
from qgis.PyQt.QtCore import QObject, pyqtSignal, pyqtSlot

from ..const import LayerType
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

    readyToQuit = pyqtSignal()

    def __init__(self, parent, settings, progress=None, log=None, isInUiThread=True):
        super().__init__(parent)

        self.settings = settings
        self.imageManager = ImageManager(settings)

        self.progress = progress or noop
        self.log = log or noop

        self._aborted = False
        self._isInUiThread = isInUiThread
        self._lock = Lock()

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
        self.readyToQuit.emit()

    @pyqtSlot()
    def buildSceneSlot(self):
        self.aborted = False
        logger.debug("Start building scene.")

        data = self.buildScene(build_layers=False)
        if data:
            self.dataReady.emit(data)

        self.taskCompleted.emit()

    @pyqtSlot(object)
    def buildLayerSlot(self, layer):
        self.aborted = False
        logger.debug("Start building layer: " + layer.name)

        for builder in self.layerBuilders(layer):
            if self.aborted:
                self.taskAborted.emit()
                return

            data = builder.build()
            if data:
                self.dataReady.emit(data)

        self.taskCompleted.emit()

    def buildScene(self, build_layers=True):
        self.aborted = False

        obj = self._buildScene()
        if build_layers:
            obj["layers"] = self._buildLayers()
        return obj

    def _buildScene(self):
        self.progress(5, "Building scene...")
        be = self.settings.baseExtent()
        mapTo3d = self.settings.mapTo3d()

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

        sp = self.settings.sceneProperties()
        p["light"] = "point" if sp.get("radioButton_PtLight") else "directional"

        if sp.get("groupBox_Fog"):
            d = sp["slider_Fog"]
            p["fog"] = {
                "color": int_color(sp["colorButton_Fog"]),
                "density": (d * d + 0.2) * 0.0002 / be.width()
            }

        if self.settings.needsProjString():
            crs = self.settings.crs
            p["proj"] = crs.toProj4() if Qgis.QGIS_VERSION_INT < 31003 else crs.toProj()

        self.log("Z scale: {}".format(mapTo3d.zScale))

        obj = {
            "type": "scene",
            "properties": p
        }
        return obj

    def _buildLayers(self):
        layers = []
        layer_list = [layer for layer in self.settings.layers() if layer.visible]
        total = len(layer_list)
        for i, layer in enumerate(layer_list):
            if self.aborted:
                break

            self.progress(int(i / total * 80) + 10, "Building {} layer...".format(layer.name))
            obj = self._buildLayer(layer)
            if obj:
                layers.append(obj)

        if self.aborted:
            return None

        return layers

    def _buildLayer(self, layer):
        layerBuilder = self._layerBuilder(layer)

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

    def layerBuilders(self, layer):
        layerBuilder = self._layerBuilder(layer)
        yield layerBuilder

        for blockBuilder in layerBuilder.blockBuilders():
            yield blockBuilder

    def _layerBuilder(self, layer):
        return LayerBuilderFactory.get(layer.type, VectorLayerBuilder)(self.settings, layer, self.imageManager)
