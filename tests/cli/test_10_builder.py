# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import json
import os
import struct

from qgis.testing import unittest

from .testbase import CLITestBase   # Enable test mode before importing plugin's other modules
from .utils import loadProject, logger
from ..utils import dataPath, outputPath
from ...core.build.builder import ThreeJSBuilder
from ...core.build.datamanager.image import ImageManager
from ...core.build.dem.builder import DEMLayerBuilder
from ...core.build.vector.builder import VectorLayerBuilder
from ...core.exportsettings import ExportSettings
from ...core.storagelocation import StorageLocation


class TestSceneBuilder(CLITestBase):

    PROJ_FILE = "testproject2/testproject2.qgs"
    SETTING_FILE = "testproject2/scene2_g2.qto3settings"

    def test01_build_scene_data(self):
        map_settings = loadProject(dataPath(self.PROJ_FILE))

        settings = ExportSettings()
        self.assertTrue(settings.loadSettingsFromFile(dataPath(self.SETTING_FILE)))
        settings.setMapSettings(map_settings)

        builder = ThreeJSBuilder(None)
        data = builder.buildScene(settings)

        logger.debug(str(data))

        self.assertEqual(data["type"], "scene")

        properties = data["properties"]
        base_extent = settings.baseExtent()
        map_to_3d = settings.mapTo3d()

        self.assertEqual(properties["baseExtent"], {
            "cx": base_extent.center().x(),
            "cy": base_extent.center().y(),
            "width": base_extent.width(),
            "height": base_extent.height()
        })
        self.assertEqual(properties["origin"], {
            "x": map_to_3d.origin.x(),
            "y": map_to_3d.origin.y(),
            "z": map_to_3d.origin.z()
        })
        self.assertEqual(properties["zScale"], map_to_3d.zScale)
        self.assertEqual(properties["light"], "directional")


class TestDEMLayerBuilder(CLITestBase):

    PROJ_FILE = "testproject2/testproject2.qgs"

    def test01_build_tiled_dem_data(self):
        SETTING_FILE = "testproject2/scene2_g2.qto3settings"
        LAYER_ID = "ascii_dem_b674e738_2b4a_46fc_8b3a_a4b3a7a4e147"

        map_settings = loadProject(dataPath(self.PROJ_FILE))

        settings = ExportSettings()
        self.assertTrue(settings.loadSettingsFromFile(dataPath(SETTING_FILE)))
        settings.setMapSettings(map_settings)

        layer = settings.getLayer(LAYER_ID)
        self.assertIsNotNone(layer)

        dem_data_dir = self.outputPath("data", "dem")
        os.makedirs(dem_data_dir, exist_ok=True)
        assetDestination = StorageLocation(
            outputDir=dem_data_dir,
            baseUrl=f"./data/dem/",
            filePrefix=settings.title()
        )

        builder = DEMLayerBuilder(layer, settings, ImageManager(map_settings), assetDestination=assetDestination)
        data = builder.build(build_contents=True)

        logger.debug(str(data))

        self.assertEqual(data["type"], "layer")
        self.assertEqual(data["id"], layer.jsLayerId)
        self.assertEqual(data["properties"]["type"], "dem")
        self.assertEqual(data["properties"]["dataType"], "grid")

        block = data["body"]["contents"][0]

        self.assertEqual(block["type"], "block")
        self.assertEqual(block["layer"], layer.jsLayerId)

        geometry = block["geometry"]
        self.assertEqual(geometry["zScale"], settings.mapTo3d().zScale)

        grid = self.loadJSONBinaryHeader(self.outputPath(geometry["grid"]["url"]))
        logger.debug(str(grid))

        self.assertEqual(grid["segments"], 10)
        self.assertEqual(grid["columns"], 10)
        self.assertEqual(grid["rows"], 10)
        self.assertEqual(grid["extent"], {
            "cx": 455.0,
            "cy": 355.0,
            "width": 100.0,
            "height": 100.0
        })

        self.assertEqual(grid["array"]["__type__"], "f32")
        self.assertTrue(grid["array"]["compressed"])

        self.assertEqual(grid["nodata"]["__type__"], "f32")
        self.assertEqual(grid["nodata"]["size"], 4)
        self.assertFalse(grid["nodata"]["compressed"])

    def test02_build_pyramid_tiled_dem_data(self):
        SETTING_FILE = "testproject2/scene2_pyramid.qto3settings"
        LAYER_ID = "srtm_62ffafc6_c8b2_4e32_8882_137d6e1bbe4c"

        map_settings = loadProject(dataPath(self.PROJ_FILE))

        settings = ExportSettings()
        self.assertTrue(settings.loadSettingsFromFile(dataPath(SETTING_FILE)))
        settings.setMapSettings(map_settings)

        layer = settings.getLayer(LAYER_ID)
        self.assertIsNotNone(layer)

        dem_data_dir = self.outputPath("data", "dem")
        os.makedirs(dem_data_dir, exist_ok=True)
        assetDestination = StorageLocation(
            outputDir=dem_data_dir,
            baseUrl=f"./data/dem/",
            filePrefix=settings.title()
        )

        builder = DEMLayerBuilder(layer, settings, ImageManager(map_settings), assetDestination=assetDestination)
        data = builder.build(build_contents=False)

        logger.debug(str(data))

        self.assertEqual(data["type"], "layer")
        self.assertEqual(data["id"], layer.jsLayerId)
        self.assertEqual(data["properties"]["type"], "dem")
        self.assertEqual(data["properties"]["dataType"], "grid")
        self.assertEqual(data["tilesetParams"], {
            "boundingBox": {
                "min": [-87958.0, -143958.0, -7.0],
                "max": [37958.0, -60042.0, 1686.0]
            },
            "gridResolution": 84.0,
            "gridCols": 1500,
            "gridRows": 1000,
            "maxLevel": 4,
            "tileSegments": 128
        })

    def loadJSONBinaryHeader(self, filename):
            with open(filename, "rb") as f:
                data = f.read()

            header_size = struct.unpack_from("<I", data)[0]
            header_end = 4 + header_size
            return json.loads(data[4:header_end])


class TestVectorLayerBuilder(CLITestBase):

    PROJ_FILE = "testproject2/testproject2.qgs"
    SETTING_FILE = "testproject2/scene2_g2.qto3settings"
    LAYER_ID = "points_230791f1_2e27_4a9d_b5e4_f137f118f216"

    def test01_build_point_layer_data(self):
        map_settings = loadProject(dataPath(self.PROJ_FILE))

        settings = ExportSettings()
        self.assertTrue(settings.loadSettingsFromFile(dataPath(self.SETTING_FILE)))
        settings.setMapSettings(map_settings)

        layer = settings.getLayer(self.LAYER_ID)
        self.assertIsNotNone(layer)

        builder = VectorLayerBuilder(layer, settings, ImageManager(map_settings))
        data = builder.build(build_contents=True)

        logger.debug(str(data))

        self.assertEqual(data["type"], "layer")
        self.assertEqual(data["id"], layer.jsLayerId)
        self.assertEqual(data["properties"]["objType"], "Cylinder")

        blocks = data["body"]["contents"]
        self.assertTrue(blocks)
        for block in blocks:
            self.assertEqual(block["type"], "block")
            self.assertEqual(block["layer"], layer.jsLayerId)
            self.assertEqual(block["featureCount"], len(block["features"]))

            for feature in block["features"]:
                geometry = feature["geom"]
                self.assertTrue(geometry["pts"])
                self.assertGreater(geometry["r"], 0)
                self.assertGreater(geometry["h"], 0)


if __name__ == "__main__":
    unittest.main()
