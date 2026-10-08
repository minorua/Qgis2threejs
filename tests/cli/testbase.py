# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from ... import conf
conf.IS_TESTING = True
conf.VALIDATE_DATA = True

from osgeo import gdal
gdal.UseExceptions()

from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QImage
from qgis.testing import unittest

from .utils import start_app, stop_app, loadProject
from ..utils import dataPath, expectedDataPath, initOutputDir, outputPath
from ..inspector.client import InspectorClient
from ...core.exportsettings import ExportSettings
from ...core.export.export import ThreeJSExporter
from ...utils.gui import openFile


MANUAL_IMAGE_CHECK = True
OUT_WIDTH, OUT_HEIGHT = (1024, 768)


class CLITestBase(unittest.TestCase):

    PROJ_FILE = None
    SETTING_FILE = None
    LAYER_ID = None

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

    def loadProject(self, filepath=None):
        if filepath is None:
            filepath = self.PROJ_FILE

        self.assertIsNotNone(filepath)

        mapSettings = loadProject(dataPath(filepath))
        self.assertIsNotNone(mapSettings)
        return mapSettings

    def loadSettings(self, filepath=None, mapSettings=None):
        if filepath is None:
            filepath = self.SETTING_FILE

        self.assertIsNotNone(filepath)

        settings = ExportSettings()
        success = settings.loadSettingsFromFile(dataPath(filepath))
        self.assertTrue(success)

        if mapSettings:
            settings.setMapSettings(mapSettings)
        return settings

    def export_webpage(self, project_path, settings_path, out_path, local_mode=False, template=None):
        mapSettings = self.loadProject(project_path)

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

        checker = InspectorClient(self.outputPath(filename))
        self.addCleanup(checker.close)

        self.assertTrue(checker.waitForLoad(), f"Failed to load {filename}")
        checker.waitForSceneLoadFinished()
        checker.renderScene()

        result = checker.checkResult()

        checker.waitIfAutoExitCancelled()

        self.assertFalse(result.errors, f"JavaScript errors found in {filename}")
        self.assertFalse(result.warnings, f"JavaScript warnings found in {filename}")

        return checker

    def check_webpage_capture(self, filename):
        """render exported web page and check page capture"""

        html_path = self.outputPath(filename)
        filename = filename.replace(".html", "_capture.png")
        image_path = self.outputPath(filename)

        checker = InspectorClient(html_path, size=QSize(OUT_WIDTH, OUT_HEIGHT))
        self.addCleanup(checker.close)
        self.assertTrue(checker.waitForLoad(), f"Failed to load {filename}")
        checker.waitForSceneLoadFinished()
        checker.renderScene()
        checker.captureToFile(image_path)

        image = QImage(image_path)
        self.assertEqual(image.size(), QSize(OUT_WIDTH, OUT_HEIGHT), "captured image size is incorrect")

        if MANUAL_IMAGE_CHECK:
            openFile(image_path)
            self.skipTest(f"Manual image verification: {image_path}")
        else:
            # TODO: Visual Regression Testing and SSIM comparison
            self.assertEqual(image, QImage(expectedDataPath(filename)), "captured image is different from expected.")

        return checker
