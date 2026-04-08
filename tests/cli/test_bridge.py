# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-27

from osgeo import gdal
gdal.UseExceptions()

from qgis.PyQt.QtCore import QFileInfo, QSize
from qgis.PyQt.QtGui import QImage
from qgis.testing import unittest

from .testbase import CLITestBase, MANUAL_IMAGE_CHECK, OUT_WIDTH, OUT_HEIGHT
from .utils import loadProject, logger
from ..utils import dataPath, expectedDataPath, assertMessagesAppearInOrder
from ...core.export.export import ImageExporter, ModelExporter
from ...gui.webview import setCurrentWebView, WEBVIEWTYPE_WEBENGINE, WEBVIEWTYPE_WEBKIT
from ...utils import openFile
from ...utils.logging import clearListHandlerLogs, getLogListHandler


class WebEngineTestBase(CLITestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        setCurrentWebView(WEBVIEWTYPE_WEBENGINE)


class WebKitTestBase(CLITestBase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        setCurrentWebView(WEBVIEWTYPE_WEBKIT)


class ExportImageTestCases:

    OUT_FILE = "scene1.png"

    def test01_export_scene1_image(self):
        """test image export with testproject1.qgs and scene1.qto3settings"""
        clearListHandlerLogs(logger)

        mapSettings = loadProject(dataPath(self.PROJ_FILE))
        out_path = self.outputPath(self.OUT_FILE)

        exporter = ImageExporter()
        exporter.loadSettings(dataPath(self.SETTING_FILE))
        exporter.setMapSettings(mapSettings)
        exporter.initWebPage(OUT_WIDTH, OUT_HEIGHT)
        exporter.export(out_path)

        # check logs
        log_handler = getLogListHandler(logger)
        log_messages = log_handler.get_messages()

        for message in log_messages:
            msg = message.lower()
            if "error" in msg:
                self.fail(f"Error log found: {message}")

            if "warning" in msg:
                logger.warning(message)

        assertMessagesAppearInOrder(log_messages, [
            "Export settings loaded from",
            "Page load finished",
            "init(",
            "emitInitialized",
            "Loading scene data",
            "Loading layer data",
            "Loading block data",
            "emitSceneLoaded",
            "Image saved to"
        ])

    def test02_check_scene1_image(self):
        """check exported image"""
        out_path = self.outputPath(self.OUT_FILE)

        image = QImage(out_path)
        self.assertEqual(image.size(), QSize(OUT_WIDTH, OUT_HEIGHT), "exported image size is incorrect")

        if MANUAL_IMAGE_CHECK:
            openFile(out_path)
            self.skipTest(f"Manual image check: {out_path}")
        else:
            self.assertEqual(image, QImage(expectedDataPath(self.OUT_FILE)), "exported image is different from expected.")


class ExportModelTestCases:

    OUT_FILE = "scene1.gltf"

    def test01_export_scene1_glTF(self):
        """test glTF export with testproject1.qgs and scene1.qto3settings"""

        mapSettings = loadProject(dataPath(self.PROJ_FILE))

        out_path = self.outputPath(self.OUT_FILE)

        exporter = ModelExporter()
        exporter.loadSettings(dataPath(self.SETTING_FILE))
        exporter.setMapSettings(mapSettings)
        exporter.initWebPage(100, 100)
        exporter.export(out_path)

        self.assertTrue(QFileInfo(out_path).size(), "Empty output file")


class TestExportImageWebEngine(WebEngineTestBase, ExportImageTestCases):
    pass


class TestExportModelWebEngine(WebEngineTestBase, ExportModelTestCases):
    pass


class TestExportImageWebKit(WebKitTestBase, ExportImageTestCases):
    pass


class TestExportModelWebKit(WebKitTestBase, ExportModelTestCases):
    pass


if __name__ == "__main__":
    unittest.main()
