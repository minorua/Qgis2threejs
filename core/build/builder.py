# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

from qgis.core import Qgis, QgsApplication

from ..const import LayerType
from .datamanager import ImageManager
from .dem.builder import DEMLayerBuilder
from .vector.builder import VectorLayerBuilder
from .pointcloud.builder import PointCloudLayerBuilder
from ...utils import int_color


LayerBuilderFactory = {
    LayerType.DEM: DEMLayerBuilder,
    LayerType.POINT: VectorLayerBuilder,
    LayerType.LINESTRING: VectorLayerBuilder,
    LayerType.POLYGON: VectorLayerBuilder,
    LayerType.POINTCLOUD: PointCloudLayerBuilder
}


class ThreeJSBuilder:

    def __init__(self, settings, progress=None, log=None):
        self.settings = settings
        self.progress = progress or dummyProgress
        self.log = log or dummyLogMessage
        self.imageManager = ImageManager(settings)

        self._canceled = False

    def buildScene(self, build_layers=True, cancelSignal=None):
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

        if build_layers:
            obj["layers"] = self.buildLayers(cancelSignal)

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


def dummyProgress(percentage=None, msg=None):
    pass


def dummyLogMessage(msg, warning=False):
    pass
