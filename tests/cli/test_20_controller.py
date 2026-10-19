# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import json
from typing import NamedTuple
from unittest.mock import Mock

from qgis.testing import unittest

from .testbase import CLITestBase   # Enable test mode before importing plugin's other modules
from ..utils import contains_instance
from ...core.exportsettings import Layer
from ...core.build.jsonbinarywriter import BinaryContainer
from ...core.controller.controller import Q3DController
from ...gui.ipc.websocketserver import WebSocketServer
from ...utils.file import pluginDir


class BuildSceneResult(NamedTuple):
    sent_data: list
    sent_layer_data: list
    sent_block_data: list
    sent_signal_data: list
    task_failures: list
    controller: Q3DController
    layer: Layer


class TestController(CLITestBase):

    PROJ_FILE = "testproject3/testproject3.qgs"
    SETTING_FILE = "testproject3/scene3_tiles.qto3settings"
    LAYER_ID = "srtm_62ffafc6_c8b2_4e32_8882_137d6e1bbe4c"

    def test01_build_scene_base64(self):
        result = self.build_scene(base64=True)   # web engine view preview
        self.assertEqual(len(result.sent_layer_data), 1)
        self.assertGreater(len(result.sent_block_data), 1)
        self.assertEqual(len(result.sent_signal_data), 2)

    def test02_build_scene_bin(self):
        socketServer = WebSocketServer(None, pluginDir("web"))

        result = self.build_scene(base64=False)  # external web browser preview
        self.assertEqual(len(result.sent_layer_data), 1)
        self.assertGreater(len(result.sent_block_data), 1)
        self.assertEqual(len(result.sent_signal_data), 2)

        for data in result.sent_data:
            self.assertTrue(data)

            b = socketServer.createMessageBytes({
                "type": WebSocketServer.TYPE_COMMAND,
                "method": "data",       # Command.LOAD_DATA
                "params": {
                    "data": data,
                    "viaQueue": True
                }
            })
            self.assertIn(b[0], (66, 74))
            if b[0] == 74:  # [J]SON
                json.loads(b[1:])
            else:   # JSON [B]inary
                self.assertTrue(data.get("_jsonbinary"))
                self.assertTrue(contains_instance(data, BinaryContainer))

    def test03_build_dem_tile_base64(self):
        self.build_dem_tile(base64=True)

    def test04_build_dem_tile_bin(self):
        self.build_dem_tile(base64=False)

    def build_scene(self, setting_file=SETTING_FILE, base64=True):
        mapSettings = self.loadProject()
        settings = self.loadSettings(setting_file, mapSettings=mapSettings)
        settings.isPreview = True
        settings.requiresJsonSerializable = base64

        layer = settings.getLayer(self.LAYER_ID)
        self.assertIsNotNone(layer)

        webPage = Mock()
        controller = Q3DController(None, settings, webPage)
        self.addCleanup(controller.teardown)

        task_failures = []
        controller.builder.taskFailed.connect(lambda *args: task_failures.append(args))

        controller.buildSceneRequest.emit(settings)
        controller.buildLayerRequest.emit(layer, None, settings)

        sent_data = []
        sent_layer_data = []
        sent_block_data = []
        sent_signal_data = []
        for call in webPage.sendData.call_args_list:
            data, viaQueue = call.args
            match data.get("type"):
                case "scene":
                    self.assertValidData(data, "SceneData")
                    self.assertFalse(sent_layer_data)
                    self.assertFalse(sent_block_data)
                case "layer":
                    self.assertValidData(data, "DEMLayerData")
                    self.assertFalse(sent_block_data)
                    sent_layer_data.append(data)
                case "block":
                    if data.get("geometry"):
                        self.assertValidData(data, "DEMBlockGridData")
                    else:
                        self.assertValidData(data, "DEMBlockMaterialData")
                    sent_block_data.append(data)
                case "signal":
                    self.assertValidData(data, "SignalData", schema_filename="preview.json")
                    self.assertEqual(data["name"], "queueCompleted")
                    self.assertTrue(data["success"])
                    sent_signal_data.append(data)
                case type_name:
                    self.fail(f"Unexpected type data: {type_name}")

            sent_data.append(data)

        self.assertFalse(task_failures)

        return BuildSceneResult(sent_data, sent_layer_data, sent_block_data, sent_signal_data,
                                task_failures, controller, layer)

    def build_dem_tile(self, base64=True):
        result = self.build_scene("testproject3/scene3_pyramid.qto3settings", base64=base64)

        layer = result.layer
        level = x = y = 0
        url = f"dem://{layer.jsLayerId}/{level}/{x}/{y}.tile"

        controller = result.controller
        controller.webPage.sendData.reset_mock()
        controller.buildTileRequest.emit(url, layer, level, x, y, False, controller.settings)

        call = controller.webPage.sendData.call_args_list[0]
        data, viaQueue = call.args
        self.assertValidData(data, "TileDataResponse", schema_filename="preview.json")

        self.assertFalse(result.task_failures)


if __name__ == "__main__":
    unittest.main()
