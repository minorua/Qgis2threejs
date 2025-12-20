# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

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

    readyToQuit = pyqtSignal()

    def __init__(self, settings, progress=None, log=None, parent=None):
        super().__init__(parent)

        self.settings = settings
        self.imageManager = ImageManager(settings)

        self.progress = progress or noop
        self.log = log or noop

        self._canceled = False

    @pyqtSlot()
    def quit(self):
        self.readyToQuit.emit()

    @pyqtSlot()
    def buildSceneSlot(self):
        logger.debug("ThreeJSBuilder: buildSceneSlot called")

        data = self.buildScene(build_layers=False)
        if data:
            self.dataReady.emit(data)
        self.taskCompleted.emit()

    @pyqtSlot(object)
    def buildLayerSlot(self, layer):
        logger.debug("ThreeJSBuilder: buildLayerSlot called for layer {}".format(layer.name))

        for builder in self.layerBuilders(layer):
            data = builder.build()
            if data:
                self.dataReady.emit(data)

        self.taskCompleted.emit()

    def buildScene(self, build_layers=True, cancelSignal=None):
        obj = self._buildScene()
        if build_layers:
            obj["layers"] = self.buildLayers(cancelSignal)
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

    def buildLayers(self, cancelSignal=None):
        if cancelSignal:
            cancelSignal.connect(self.cancel)

        layers = []
        layer_list = [layer for layer in self.settings.layers() if layer.visible]
        total = len(layer_list)
        for i, layer in enumerate(layer_list):
            self.progress(int(i / total * 80) + 10, "Building {} layer...".format(layer.name))

            if self.canceled:
                break

            obj = self.buildLayer(layer, cancelSignal)
            if obj:
                layers.append(obj)

        if cancelSignal:
            cancelSignal.disconnect(self.cancel)

        return layers

    def buildLayer(self, layer, cancelSignal=None):
        builder = LayerBuilderFactory.get(layer.type, VectorLayerBuilder)(self.settings, layer, self.imageManager)
        return builder.build(cancelSignal=cancelSignal)

    def layerBuilders(self, layer):
        builder = LayerBuilderFactory.get(layer.type, VectorLayerBuilder)(self.settings, layer, self.imageManager)
        yield builder

        for builder in builder.subBuilders():
            yield builder

    # TODO: use threading.Lock
    @property
    def canceled(self):
        if not self._canceled:
            QgsApplication.processEvents()
        return self._canceled

    @canceled.setter
    def canceled(self, value):
        self._canceled = value

    def cancel(self):
        self._canceled = True
