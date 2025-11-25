# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-27

from qgis.PyQt.QtCore import QFileInfo, QSize, QUrl
from qgis.PyQt.QtGui import QImage
from qgis.testing import unittest

from ..test_utils.unit import start_app, stop_app, logger
from ..test_utils.utils import dataPath, expectedDataPath, initOutputDir, outputPath, loadProject as _loadProject, assertMessagesAppearInOrder
from ..test_utils.webpage_check import WebPageCapturer, WebPageErrorChecker
from ...core.export.export import ThreeJSExporter, ImageExporter, ModelExporter
from ...core.mapextent import MapExtent
from ...gui.webview import setCurrentWebView, WEBVIEWTYPE_WEBENGINE, WEBVIEWTYPE_WEBKIT
from ...utils import openFile
from ...utils.logging import clearListHandlerLogs, getLogListHandler

OUT_WIDTH, OUT_HEIGHT = (1024, 768)
TEX_WIDTH, TEX_HEIGHT = (1024, 1024)

MANUAL_PAGE_CHECK = True
MANUAL_IMAGE_CHECK = True


def loadProject(filename):
    """load a project"""
    mapSettings = _loadProject(filename)

    # extent
    MapExtent(mapSettings.extent().center(),
                mapSettings.extent().height(),
                mapSettings.extent().height(), 0).toMapSettings(mapSettings)

    # texture base size
    mapSettings.setOutputSize(QSize(TEX_WIDTH, TEX_HEIGHT))

    return mapSettings


class ExportTestBase:

    @classmethod
    def initOutputDir(cls):
        initOutputDir(cls.__name__[4:])

    @classmethod
    def outputPath(cls, *subdirs):
        return outputPath(cls.__name__[4:], *subdirs)


class TestExportWeb(unittest.TestCase, ExportTestBase):

    OUT_FILE = "scene1.html"
    PROJ_FILE = "testproject1.qgs"
    SETTING_FILE = "scene1.qto3settings"
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
        exporter.settings.jsonSerializable = local_mode
        exporter.setMapSettings(mapSettings)

        err = exporter.export(out_path)
        assert err, "export failed"

    def check_webpage(self, filename):
        """check JavaScript errors and warnings in exported web page"""

        url = QUrl.fromLocalFile(self.outputPath(filename))
        wpv = WebPageErrorChecker(url)
        result = wpv.check()

        if MANUAL_PAGE_CHECK:
            openFile(self.outputPath(filename))

        assert not result.errors, f"JavaScript errors found in {filename}"
        assert not result.warnings, f"JavaScript warnings found in {filename}"

    def check_webpage_capture(self, filename):
        """render exported web page and check page capture"""

        url = QUrl.fromLocalFile(self.outputPath(filename))
        # url = QUrl(url.toString() + "#cx=-20&cy=34&cz=16&tx=-2&ty=-8&tz=0")

        filename = filename.replace(".html", "_capture.png")
        image_path = self.outputPath(filename)

        wpc = WebPageCapturer(url, QSize(OUT_WIDTH, OUT_HEIGHT))
        # wpc.runScript('document.getElementById("progress").style.display = "none";')  # hide progress bar
        wpc.waitForDataLoadFinished()
        wpc.renderScene()
        wpc.captureToFile(image_path)

        if MANUAL_IMAGE_CHECK:
            openFile(image_path)
            self.skipTest(f"Manual image verification: {image_path}")
        else:
            # TODO: Visual Regression Testing and SSIM comparison
            assert QImage(image_path) == QImage(expectedDataPath(filename)), "captured image is different from expected."


class TestExportWebLocalMode(TestExportWeb):
    LOCAL_MODE = True


class WebEngineTestBase(ExportTestBase):

    @classmethod
    def setUpClass(cls):
        cls.initOutputDir()
        start_app()
        setCurrentWebView(WEBVIEWTYPE_WEBENGINE)

    @classmethod
    def tearDownClass(cls):
        stop_app()


class WebKitTestBase(ExportTestBase):

    @classmethod
    def setUpClass(cls):
        cls.initOutputDir()
        start_app()
        setCurrentWebView(WEBVIEWTYPE_WEBKIT)

    @classmethod
    def tearDownClass(cls):
        stop_app()


class ExportImageTestCases(ExportTestBase):

    OUT_FILE = "scene1.png"
    PROJ_FILE = "testproject1.qgs"
    SETTING_FILE = "scene1.qto3settings"

    def setUp(self):
        clearListHandlerLogs(logger)

    def test01_export_scene1_image(self):
        """test image export with testproject1.qgs and scene1.qto3settings"""

        mapSettings = loadProject(dataPath(self.PROJ_FILE))
        out_path = self.outputPath(self.OUT_FILE)

        exporter = ImageExporter()
        exporter.loadSettings(dataPath(self.SETTING_FILE))
        exporter.setMapSettings(mapSettings)
        exporter.initWebPage(OUT_WIDTH, OUT_HEIGHT)

        err = exporter.export(out_path)
        assert not err, err

    def test02_check_logs(self):
        log_handler = getLogListHandler(logger)
        assert log_handler, "ListHandler not found in logger"

        log_messages = log_handler.get_messages()

        for message in log_messages:
            msg = message.lower()
            if "error" in msg:
                assert False, f"Error log found: {message}"

            if "warning" in msg:
                logger.warning(message)

        assertMessagesAppearInOrder(log_messages, [
            "Export settings loaded from",
            "Page load finished",
            "init(",
            "emitInitialized",
            'loadStart("LYRS", true)',
            "loadJSONObject(",
            'loadEnd("LYRS")',
            "emitSceneLoaded",
            "Image saved to"
        ])

    def test03_check_scene1_image(self):
        """check exported image"""
        out_path = self.outputPath(self.OUT_FILE)
        if MANUAL_IMAGE_CHECK:
            openFile(out_path)
            self.skipTest(f"Manual image check: {out_path}")
        else:
            assert QImage(out_path) == QImage(expectedDataPath(self.OUT_FILE)), "exported image is different from expected."


class ExportModelTestCases(ExportTestBase):

    def test01_export_scene1_glTF(self):
        """test glTF export with testproject1.qgs and scene1.qto3settings"""

        mapSettings = loadProject(dataPath("testproject1.qgs"))

        filename = "scene1.gltf"
        out_path = self.outputPath(filename)

        exporter = ModelExporter()
        exporter.loadSettings(dataPath("scene1.qto3settings"))
        exporter.setMapSettings(mapSettings)
        exporter.initWebPage(100, 100)

        err = exporter.export(out_path)

        assert not err, err
        assert QFileInfo(out_path).size(), "Empty output file"


class TestExportImageWebEngine(unittest.TestCase, WebEngineTestBase, ExportImageTestCases):
    setUpClass = WebEngineTestBase.setUpClass
    tearDownClass = WebEngineTestBase.tearDownClass


class TestExportModelWebEngine(unittest.TestCase, WebEngineTestBase, ExportModelTestCases):
    setUpClass = WebEngineTestBase.setUpClass
    tearDownClass = WebEngineTestBase.tearDownClass


class TestExportImageWebKit(unittest.TestCase, WebKitTestBase, ExportImageTestCases):
    setUpClass = WebKitTestBase.setUpClass
    tearDownClass = WebKitTestBase.tearDownClass


class TestExportModelWebKit(unittest.TestCase, WebKitTestBase, ExportModelTestCases):
    setUpClass = WebKitTestBase.setUpClass
    tearDownClass = WebKitTestBase.tearDownClass


if __name__ == "__main__":
    unittest.main()
