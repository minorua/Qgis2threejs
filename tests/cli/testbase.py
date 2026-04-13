# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from osgeo import gdal
gdal.UseExceptions()

from qgis.PyQt.QtCore import QSize, QUrl
from qgis.PyQt.QtGui import QImage
from qgis.testing import unittest

from .utils import start_app, stop_app, loadProject
from ..utils import expectedDataPath, initOutputDir, outputPath
from ..webpage_check import WebPageCapturer, WebPageErrorChecker
from ...core.export.export import ThreeJSExporter
from ...utils import openFile


MANUAL_PAGE_CHECK = True
MANUAL_IMAGE_CHECK = True

OUT_WIDTH, OUT_HEIGHT = (1024, 768)


class CLITestBase(unittest.TestCase):

    PROJ_FILE = "testproject1/testproject1.qgs"
    SETTING_FILE = "testproject1/scene1.qto3settings"

    @classmethod
    def setUpClass(cls):
        cls.initOutputDir()
        start_app()

    @classmethod
    def tearDownClass(cls):
        stop_app()

    @classmethod
    def initOutputDir(cls):
        initOutputDir(cls.__name__[4:])

    @classmethod
    def outputPath(cls, *subdirs):
        return outputPath(cls.__name__[4:], *subdirs)

    def export_webpage(self, project_path, settings_path, out_path, local_mode=False, template=None):
        mapSettings = loadProject(project_path)

        exporter = ThreeJSExporter()
        exporter.loadSettings(settings_path)
        exporter.settings.localMode = local_mode
        exporter.settings.requiresJsonSerializable = local_mode
        if template:
            exporter.settings.setTemplate(template)
        exporter.setMapSettings(mapSettings)
        exporter.export(out_path)

    def check_webpage(self, filename):
        """check JavaScript errors and warnings in exported web page"""

        url = QUrl.fromLocalFile(self.outputPath(filename))
        checker = WebPageErrorChecker(url)
        result = checker.check()

        if MANUAL_PAGE_CHECK:
            openFile(self.outputPath(filename))

        self.assertFalse(result.errors, f"JavaScript errors found in {filename}")
        self.assertFalse(result.warnings, f"JavaScript warnings found in {filename}")

        return checker

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

        return wpc
