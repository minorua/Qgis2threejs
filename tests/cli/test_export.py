# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-27

from osgeo import gdal
gdal.UseExceptions()

from qgis.PyQt.QtCore import QSize, QUrl
from qgis.PyQt.QtGui import QImage
from qgis.testing import unittest

from .testbase import CLITestBase, MANUAL_PAGE_CHECK, MANUAL_IMAGE_CHECK
from .utils import start_app, stop_app, loadProject, logger
from ..utils import dataPath, expectedDataPath
from ..webpage_check import WebPageCapturer, WebPageErrorChecker
from ...core.export.export import ThreeJSExporter
from ...utils import openFile

OUT_WIDTH, OUT_HEIGHT = (1024, 768)


class TestExportWeb(unittest.TestCase, CLITestBase):

    OUT_FILE = "scene1.html"
    LOCAL_MODE = False

    @classmethod
    def setUpClass(cls):
        cls.initOutputDir()
        start_app()

    @classmethod
    def tearDownClass(cls):
        stop_app()

    def test01_export_scene1_webpage(self):
        """test web page export"""
        out_path = self.outputPath(self.OUT_FILE)

        self.export_webpage(
            project_path=dataPath(self.PROJ_FILE),
            settings_path=dataPath(self.SETTING_FILE),
            out_path=out_path,
            local_mode=self.LOCAL_MODE
        )

        logger.info(f"exported web page: {out_path}")

    def test02_check_scene1_webpage(self):
        self.check_webpage(self.OUT_FILE)

    def test03_check_scene1_webpage_capture(self):
        self.check_webpage_capture(self.OUT_FILE)

    def export_webpage(self, project_path, settings_path, out_path, local_mode=False):
        mapSettings = loadProject(project_path)

        exporter = ThreeJSExporter()
        exporter.loadSettings(settings_path)
        exporter.settings.localMode = local_mode
        exporter.settings.requiresJsonSerializable = local_mode
        exporter.setMapSettings(mapSettings)
        exporter.export(out_path)

    def check_webpage(self, filename):
        """check JavaScript errors and warnings in exported web page"""

        url = QUrl.fromLocalFile(self.outputPath(filename))
        wpv = WebPageErrorChecker(url)
        result = wpv.check()

        if MANUAL_PAGE_CHECK:
            openFile(self.outputPath(filename))

        self.assertFalse(result.errors, f"JavaScript errors found in {filename}")
        self.assertFalse(result.warnings, f"JavaScript warnings found in {filename}")

    def check_webpage_capture(self, filename):
        """render exported web page and check page capture"""

        url = QUrl.fromLocalFile(self.outputPath(filename))
        # url = QUrl(url.toString() + "#cx=-20&cy=34&cz=16&tx=-2&ty=-8&tz=0")

        filename = filename.replace(".html", "_capture.png")
        image_path = self.outputPath(filename)

        wpc = WebPageCapturer(url, QSize(OUT_WIDTH, OUT_HEIGHT))
        # wpc.runScript('document.getElementById("progress").style.display = "none";')  # hide progress bar
        wpc.waitForSceneLoadFinished()
        wpc.renderScene()
        wpc.captureToFile(image_path)

        image = QImage(image_path)
        self.assertEqual(image.size(), QSize(OUT_WIDTH, OUT_HEIGHT), "captured image size is incorrect")

        if MANUAL_IMAGE_CHECK:
            openFile(image_path)
            self.skipTest(f"Manual image verification: {image_path}")
        else:
            # TODO: Visual Regression Testing and SSIM comparison
            self.assertEqual(image, QImage(expectedDataPath(filename)), "captured image is different from expected.")


class TestExportWebLocalMode(TestExportWeb):

    OUT_FILE = "scene1.html"
    LOCAL_MODE = True


if __name__ == "__main__":
    unittest.main()
