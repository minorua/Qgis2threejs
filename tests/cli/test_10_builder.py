# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os

from qgis.core import QgsCoordinateTransform, QgsPointXY, QgsProject
from qgis.testing import unittest

from .testbase import CLITestBase   # Enable test mode before importing plugin's other modules
from ...core.build.builder import ThreeJSBuilder
from ...core.build.datamanager.image import ImageManager
from ...core.build.dem.builder import DEMLayerBuilder
from ...core.build.jsonbinarywriter import BinaryContainer, JSONBinaryWriter
from ...core.build.vector.builder import VectorLayerBuilder
from ...core.mapextent import MapExtent
from ...core.storagelocation import StorageLocation


class TestJSONBinaryWriter(CLITestBase):

    def test01_bytes(self):
        writer = JSONBinaryWriter({
            "first": BinaryContainer(b"\x01\x02", "I8"),
            "second": BinaryContainer(b"\x03", "I8"),
            "third": 3
        })
        data = writer.toBytes()
        jsondata, binarydata = self.readJSONBinaryData(data)

        self.assertEqual(jsondata["first"]["offset"], 0)
        self.assertEqual(jsondata["second"]["offset"], 2)
        self.assertEqual(binarydata, b"\x01\x02\x03")

    def test02_json(self):
        source = {
            "first": 1,
            "second": "2"
        }
        writer = JSONBinaryWriter(source)
        data = writer.toBytes()
        jsondata, binarydata = self.readJSONBinaryData(data)

        self.assertEqual(jsondata, source)
        self.assertIs(binarydata, b"")


class TestSceneBuilder(CLITestBase):

    PROJ_FILE = "testproject2/testproject2.qgs"
    SETTING_FILE = "testproject2/scene2_g2.qto3settings"

    def test01_build_scene_data(self):
        mapSettings = self.loadProject()
        settings = self.loadSettings(mapSettings=mapSettings)

        builder = ThreeJSBuilder(None)
        data = builder.buildScene(settings)
        self.assertValidData(data, "SceneData")

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

    def test01_build_simple_dem_data(self):
        mapSettings = self.loadProject("testproject1/testproject1.qgs")
        settings = self.loadSettings("testproject1/scene1_g1.qto3settings", mapSettings)
        layer = settings.getLayer("dem_srtm3020150914165149263")
        self.assertIsNotNone(layer)
        self.assertNotEqual(layer.mapLayer.crs(), settings.crs)

        builder = DEMLayerBuilder(layer, settings, ImageManager(mapSettings))

        transform = QgsCoordinateTransform(layer.mapLayer.crs(), settings.crs, QgsProject.instance())
        settings._baseExtent = MapExtent.fromRect(transform.transformBoundingBox(layer.mapLayer.extent()))

        data = builder.build()
        self.assertValidData(data, "DEMLayerData")

        self.assertEqual(data["id"], layer.jsLayerId)
        self.assertEqual(data["properties"]["dataType"], "grid")

        settings._baseExtent = MapExtent(QgsPointXY(0, -200000), 100, 100)
        self.assertIsNone(builder.build())

    def test02_build_tiled_dem_data(self):
        mapSettings = self.loadProject("testproject2/testproject2.qgs")
        settings = self.loadSettings("testproject2/scene2_g2.qto3settings", mapSettings)
        layer = settings.getLayer("ascii_dem_b674e738_2b4a_46fc_8b3a_a4b3a7a4e147")
        self.assertIsNotNone(layer)

        dem_data_dir = self.outputPath("data", "dem")
        os.makedirs(dem_data_dir, exist_ok=True)
        assetDestination = StorageLocation(
            outputDir=dem_data_dir,
            baseUrl=f"./data/dem/",
            filePrefix=settings.title()
        )

        builder = DEMLayerBuilder(layer, settings, ImageManager(mapSettings), assetDestination=assetDestination)

        data = builder.build(build_contents=True)
        self.assertValidData(data, "DEMLayerData")

        self.assertEqual(data["id"], layer.jsLayerId)
        self.assertEqual(data["properties"]["dataType"], "grid")

        block = data["body"]["contents"][0]

        self.assertValidData(block, "DEMBlockData")
        self.assertEqual(block["layer"], layer.jsLayerId)

        geometry = block["geometry"]
        self.assertEqual(geometry["zScale"], settings.mapTo3d().zScale)

        grid, _ = self.loadJSONBinaryFile(self.outputPath(geometry["grid"]["url"]))
        self.assertValidData(grid, "GridGeomDataBinaryJSON")

        self.assertEqual(grid["segments"], 10)
        self.assertEqual(grid["columns"], 10)
        self.assertEqual(grid["rows"], 10)
        self.assertEqual(grid["extent"], {
            "cx": 455.0,
            "cy": 355.0,
            "width": 100.0,
            "height": 100.0
        })

        self.assertEqual(grid["array"]["_type"], "f32")
        self.assertTrue(grid["array"]["compressed"])

        self.assertEqual(grid["nodata"]["_type"], "f32")
        self.assertEqual(grid["nodata"]["size"], 4)
        self.assertFalse(grid["nodata"]["compressed"])

    def test03_build_pyramid_tiled_dem_data(self):
        mapSettings = self.loadProject("testproject3/testproject3.qgs")
        settings = self.loadSettings("testproject3/scene3_pyramid.qto3settings", mapSettings)
        layer = settings.getLayer("srtm_62ffafc6_c8b2_4e32_8882_137d6e1bbe4c")
        self.assertIsNotNone(layer)

        dem_data_dir = self.outputPath("data", "dem")
        os.makedirs(dem_data_dir, exist_ok=True)
        assetDestination = StorageLocation(
            outputDir=dem_data_dir,
            baseUrl=f"./data/dem/",
            filePrefix=settings.title()
        )

        builder = DEMLayerBuilder(layer, settings, ImageManager(mapSettings), assetDestination=assetDestination)

        data = builder.build(build_contents=False)
        self.assertValidData(data, "DEMLayerData")

        self.assertEqual(data["id"], layer.jsLayerId)
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


class TestVectorLayerBuilder(CLITestBase):

    PROJ_FILE = "testproject2/testproject2.qgs"
    SETTING_FILE = "testproject2/scene2_g2.qto3settings"
    LAYER_ID = "points_230791f1_2e27_4a9d_b5e4_f137f118f216"

    def test01_build_point_layer_data(self):
        mapSettings = self.loadProject()
        settings = self.loadSettings(mapSettings=mapSettings)
        layer = settings.getLayer(self.LAYER_ID)
        self.assertIsNotNone(layer)

        builder = VectorLayerBuilder(layer, settings, ImageManager(mapSettings))

        data = builder.build(build_contents=True)
        self.assertValidData(data, "VectorLayerData", convert_tuples=True)

        self.assertEqual(data["id"], layer.jsLayerId)
        self.assertEqual(data["properties"]["objType"], "Cylinder")

        blocks = data["body"]["contents"]
        self.assertTrue(blocks)
        for block in blocks:
            self.assertValidData(block, "FeatureBlockData", convert_tuples=True)
            self.assertEqual(block["layer"], layer.jsLayerId)
            self.assertEqual(block["featureCount"], len(block["features"]))

            for feature in block["features"]:
                geometry = feature["geom"]
                self.assertTrue(geometry["pts"])
                self.assertGreater(geometry["r"], 0)
                self.assertGreater(geometry["h"], 0)


if __name__ == "__main__":
    unittest.main()
