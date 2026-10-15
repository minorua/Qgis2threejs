# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

"""Benchmark DEM layer data generation time in tiles mode.

Based on TestDEMLayerBuilder.test02_build_tiled_dem_data in tests/cli/test_10_builder.py.

Usage:
    c:/osgeo4w/bin/python-qgis.bat -m Qgis2threejs.tests.benchmarks.benchmark_dem [-n REPEAT] [-w WARMUP]
"""

import argparse
import os
import statistics
import sys
import time

from qgis.testing import unittest

from ..cli.testbase import CLITestBase   # Enable test mode before importing plugin's other modules
from ...core.build.datamanager.image import ImageManager
from ...core.build.dem.builder import DEMLayerBuilder
from ...core.storagelocation import StorageLocation

REPEAT = 5
WARMUP = 1


class BenchmarkDEM(CLITestBase):

    PROJ_FILE = "testproject3/testproject3.qgs"
    SETTING_FILE = "testproject3/scene3_tiles.qto3settings"
    LAYER_ID = "srtm_62ffafc6_c8b2_4e32_8882_137d6e1bbe4c"

    def test_build_tiled_dem_data(self):
        mapSettings = self.loadProject()
        settings = self.loadSettings(mapSettings=mapSettings)
        layer = settings.getLayer(self.LAYER_ID)
        self.assertIsNotNone(layer)

        dem_data_dir = self.outputPath("data", "dem")
        os.makedirs(dem_data_dir, exist_ok=True)
        assetDestination = StorageLocation(
            outputDir=dem_data_dir,
            baseUrl="./data/dem/",
            filePrefix=settings.title()
        )

        def build():
            builder = DEMLayerBuilder(layer, settings, ImageManager(mapSettings), assetDestination=assetDestination)
            t0 = time.perf_counter()
            data = builder.build(build_contents=True)
            elapsed = time.perf_counter() - t0
            self.assertIsNotNone(data)
            return elapsed

        for _ in range(WARMUP):
            build()

        times = [build() for _ in range(REPEAT)]

        print(f"\nDEM build time in tiles mode ({REPEAT} runs, {WARMUP} warmup):")
        for i, t in enumerate(times, 1):
            print(f"  run {i}: {t:.4f} s")
        print(f"  min: {min(times):.4f} s / mean: {statistics.mean(times):.4f} s / "
              f"median: {statistics.median(times):.4f} s / max: {max(times):.4f} s")
        if len(times) > 1:
            print(f"  stdev: {statistics.stdev(times):.4f} s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-n", "--repeat", type=int, default=REPEAT, help="number of measured runs")
    parser.add_argument("-w", "--warmup", type=int, default=WARMUP, help="number of warmup runs")
    args, rest = parser.parse_known_args()
    REPEAT = max(1, args.repeat)
    WARMUP = max(0, args.warmup)
    unittest.main(argv=[sys.argv[0]] + rest)
