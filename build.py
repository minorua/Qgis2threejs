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
from .datamanager import ImageManager
from .builddem import DEMLayerBuilder
from .buildvector import VectorLayerBuilder
from .qgis2threejstools import logMessage
from . import q3dconst


class ThreeJSBuilder:

    def __init__(self, settings, progress=None):
        self.settings = settings
        self.progress = progress or dummyProgress
        self.imageManager = ImageManager(settings)

    def buildScene(self, build_layers=True):
        self.progress(10, "Building scene")
        crs = self.settings.crs
        extent = self.settings.baseExtent
        rect = extent.unrotatedRect()
        mapTo3d = self.settings.mapTo3d()
        wgs84Center = self.settings.wgs84Center()

        obj = {
            "type": "scene",
            "properties": {
                "height": mapTo3d.planeHeight,
                "width": mapTo3d.planeWidth,
                "baseExtent": [rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()],
                "crs": str(crs.authid()),
                "proj": crs.toProj4(),
                "rotation": extent.rotation(),
                "wgs84Center": {
                    "lat": wgs84Center.y(),
                    "lon": wgs84Center.x()
                },
                "zExaggeration": mapTo3d.verticalExaggeration,
                "zShift": mapTo3d.verticalShift
            }
        }

        if build_layers:
            obj["layers"] = self.buildLayers()

        return obj

    def buildLayers(self):
        layers = []
        layer_list = [layer for layer in self.settings.getLayerList() if layer.visible]
        total = len(layer_list)
        for i, layer in enumerate(layer_list):
            self.progress(int(i / total * 80) + 10, "Building {} layer".format(layer.name))
            layers.append(self.buildLayer(layer))

        return layers

    def buildLayer(self, layer):
        if layer.geomType == q3dconst.TYPE_DEM:
            builder = DEMLayerBuilder(self.settings, self.imageManager, layer)
        else:
            builder = VectorLayerBuilder(self.settings, self.imageManager, layer)
        return builder.build()

    def builders(self, layer):
        if layer.geomType == q3dconst.TYPE_DEM:
            builder = DEMLayerBuilder(self.settings, self.imageManager, layer)
        else:
            builder = VectorLayerBuilder(self.settings, self.imageManager, layer)
        yield builder

        for blockBuilder in builder.blocks():
            yield blockBuilder


def dummyProgress(percentage=None, msg=None):
    pass
