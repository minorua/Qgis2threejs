# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

"""Benchmark DEM generation and dispatch through Q3DController.

Based on TestController.test01_build_scene in tests/cli/test_20_controller.py.

Usage:
    c:/osgeo4w/bin/python-qgis.bat -m Qgis2threejs.tests.benchmarks.benchmark_controller_dem [--base64 | --bin] [-n REPEAT] [-w WARMUP]
"""

import argparse
import statistics
import sys
import time
from unittest.mock import Mock

from qgis.testing import unittest

from ..cli.testbase import CLITestBase   # Enable test mode before importing plugin's other modules
from ...core.controller.controller import Q3DController
from ...gui.ipc.websocketserver import WebSocketServer
from ...utils.file import pluginDir

BASE64 = True
REPEAT = 5
WARMUP = 1


class BenchmarkControllerDEM(CLITestBase):

    PROJ_FILE = "testproject3/testproject3.qgs"
    SETTING_FILE = "testproject3/scene3_tiles.qto3settings"
    LAYER_ID = "srtm_62ffafc6_c8b2_4e32_8882_137d6e1bbe4c"

    def test_build_scene(self):
        mapSettings = self.loadProject()
        settings = self.loadSettings(mapSettings=mapSettings)
        layer = settings.getLayer(self.LAYER_ID)
        self.assertIsNotNone(layer)

        settings.isPreview = True
        settings.requiresJsonSerializable = BASE64

        webPage = Mock()
        controller = Q3DController(None, settings, webPage)
        self.addCleanup(controller.teardown)

        socketServer = WebSocketServer(None, pluginDir("web"))

        task_failures = []
        controller.builder.taskFailed.connect(lambda *args: task_failures.append(args))

        def build_and_create_msg():
            webPage.sendData.reset_mock()
            task_failures.clear()

            start = time.perf_counter()
            controller.buildLayerRequest.emit(layer, None, settings)

            if task_failures:
                self.fail(f"DEM build failed: {task_failures[0]}")

            layer_count = block_count = signal_count = 0
            for call in webPage.sendData.call_args_list:
                data, viaQueue = call.args
                self.assertTrue(data)

                b = socketServer.createMessageBytes({
                    "type": WebSocketServer.TYPE_COMMAND,
                    "method": "data",       # Command.LOAD_DATA
                    "params": {
                        "data": data,
                        "viaQueue": viaQueue
                    }
                })

                match data.get("type"):
                    case "layer":
                        layer_count += 1
                    case "block":
                        block_count += 1
                    case "signal":
                        signal_count += 1

            elapsed = time.perf_counter() - start
            return elapsed, layer_count, block_count, signal_count

        for _ in range(WARMUP):
            build_and_create_msg()

        results = [build_and_create_msg() for _ in range(REPEAT)]
        print(f"\nQ3DController DEM build and dispatch ({REPEAT} runs, {WARMUP} warmup):")
        for i, (elapsed, layer_count, block_count, signal_count) in enumerate(results, 1):
            print(f"  run {i}: {elapsed:.4f} s, {layer_count} layers, {block_count} blocks, {signal_count} signals")

        times = [result[0] for result in results]
        print(f"  min: {min(times):.4f} s / mean: {statistics.mean(times):.4f} s / "
              f"median: {statistics.median(times):.4f} s / max: {max(times):.4f} s")
        if len(times) > 1:
            print(f"  stdev: {statistics.stdev(times):.4f} s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    base64_group = parser.add_mutually_exclusive_group()
    base64_group.add_argument("--base64", dest="base64", action="store_true", help="enable base64 conversion (default)")
    base64_group.add_argument("--bin", dest="base64", action="store_false", help="disable base64 conversion")
    parser.set_defaults(base64=BASE64)
    parser.add_argument("-n", "--repeat", type=int, default=REPEAT, help="number of measured runs")
    parser.add_argument("-w", "--warmup", type=int, default=WARMUP, help="number of warmup runs")
    args, rest = parser.parse_known_args()
    BASE64 = args.base64
    REPEAT = max(1, args.repeat)
    WARMUP = max(0, args.warmup)
    unittest.main(argv=[sys.argv[0]] + rest)
