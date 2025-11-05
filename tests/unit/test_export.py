# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-27

from qgis.PyQt.QtCore import QEventLoop, QFileInfo, QSize, QTimer, QUrl
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.testing import unittest

from .utils import start_app, stop_app
from ..utils import dataPath, expectedDataPath, outputPath, loadProject as _loadProject
from ...core.export.export import ThreeJSExporter, ImageExporter, ModelExporter
from ...core.mapextent import MapExtent
from ...gui.webview import setCurrentWebView, WEBVIEWTYPE_WEBENGINE, WEBVIEWTYPE_WEBKIT
from ...gui.webkitview import Q3DWebKitPage

OUT_WIDTH, OUT_HEIGHT = (1024, 768)
TEX_WIDTH, TEX_HEIGHT = (1024, 1024)


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


class TestExportWeb(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_app()

    @classmethod
    def tearDownClass(cls):
        stop_app()

    def test01_export_scene1_webpage(self):
        """test web page export"""

        mapSettings = loadProject(dataPath("testproject1.qgs"))

        out_path = outputPath("scene1.html")

        exporter = ThreeJSExporter()
        exporter.loadSettings(dataPath("scene1.qto3settings"))
        exporter.setMapSettings(mapSettings)
        err = exporter.export(out_path)

        assert err, "export failed"

    def test02_export_scene1_webpage_localmode(self):
        """test web page export in local mode"""

        mapSettings = loadProject(dataPath("testproject1.qgs"))

        out_path = outputPath("scene1LC.html")

        exporter = ThreeJSExporter()
        exporter.loadSettings(dataPath("scene1.qto3settings"))
        exporter.settings.localMode = exporter.settings.jsonSerializable = True

        exporter.setMapSettings(mapSettings)
        err = exporter.export(out_path)

        assert err, "export failed"

    def test03_check_scene1_webpage(self):
        """render exported web page and check page capture"""

        html_path = outputPath("scene1.html")

        url = QUrl.fromLocalFile(html_path)
        url = QUrl(url.toString() + "#cx=-20&cy=34&cz=16&tx=-2&ty=-8&tz=0")

        loop = QEventLoop()
        page = Q3DWebKitPage()
        page.setViewportSize(QSize(OUT_WIDTH, OUT_HEIGHT))
        page.loadFinished.connect(loop.quit)
        page.mainFrame().setUrl(url)
        loop.exec()

        page.mainFrame().evaluateJavaScript('document.getElementById("progress").style.display = "none";')

        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(100)
        while page.mainFrame().evaluateJavaScript("app.loadingManager.isLoading"):
            loop.exec()

        timer.stop()

        image = QImage(OUT_WIDTH, OUT_HEIGHT, QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        page.mainFrame().render(painter)
        painter.end()

        filename = "scene1_qwebpage.png"
        image.save(outputPath(filename))
        assert QImage(outputPath(filename)) == QImage(expectedDataPath(filename)), "captured image is different from expected."


class WebEngineTestBase:

    @classmethod
    def setUpClass(cls):
        start_app()
        setCurrentWebView(WEBVIEWTYPE_WEBENGINE)

    @classmethod
    def tearDownClass(cls):
        stop_app()


class WebKitTestBase:

    @classmethod
    def setUpClass(cls):
        start_app()
        setCurrentWebView(WEBVIEWTYPE_WEBKIT)

    @classmethod
    def tearDownClass(cls):
        stop_app()


class ExportImageTestBase:

    def test01_export_scene1_image(self):
        """test image export with testproject1.qgs and scene1.qto3settings"""

        mapSettings = loadProject(dataPath("testproject1.qgs"))

        filename = "scene1.png"
        out_path = outputPath(filename)

        exporter = ImageExporter()
        exporter.loadSettings(dataPath("scene1.qto3settings"))
        exporter.setMapSettings(mapSettings)
        exporter.initWebPage(OUT_WIDTH, OUT_HEIGHT)

        err = exporter.export(out_path)

        assert not err, err
        assert QImage(out_path) == QImage(expectedDataPath(filename)), "exported image is different from expected."


class ExportModelTestBase:

    def test01_export_scene1_glTF(self):
        """test glTF export with testproject1.qgs and scene1.qto3settings"""

        mapSettings = loadProject(dataPath("testproject1.qgs"))

        filename = "scene1.gltf"
        out_path = outputPath(filename)

        exporter = ModelExporter()
        exporter.loadSettings(dataPath("scene1.qto3settings"))
        exporter.setMapSettings(mapSettings)
        exporter.initWebPage(100, 100)

        err = exporter.export(out_path)

        assert not err, err
        assert QFileInfo(out_path).size(), "Empty output file"


class TestExportImageWebEngine(unittest.TestCase, WebEngineTestBase, ExportImageTestBase):
    setUpClass = WebEngineTestBase.setUpClass
    tearDownClass = WebEngineTestBase.tearDownClass


class TestExportModelWebEngine(unittest.TestCase, WebEngineTestBase, ExportModelTestBase):
    setUpClass = WebEngineTestBase.setUpClass
    tearDownClass = WebEngineTestBase.tearDownClass


class TestExportImageWebKit(unittest.TestCase, WebKitTestBase, ExportImageTestBase):
    setUpClass = WebKitTestBase.setUpClass
    tearDownClass = WebKitTestBase.tearDownClass


class TestExportModelWebKit(unittest.TestCase, WebKitTestBase, ExportModelTestBase):
    setUpClass = WebKitTestBase.setUpClass
    tearDownClass = WebKitTestBase.tearDownClass


if __name__ == "__main__":
    unittest.main()
