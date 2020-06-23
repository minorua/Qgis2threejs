# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2018-11-27

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
from PyQt5.QtCore import QEventLoop, QFileInfo, QSize, QTimer, QUrl
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWebKitWidgets import QWebPage
from qgis.testing import unittest

from Qgis2threejs.export import ThreeJSExporter, ImageExporter, ModelExporter
from Qgis2threejs.mapextent import MapExtent
from Qgis2threejs.tests.utilities import dataPath, expectedDataPath, outputPath, loadProject

OUT_WIDTH, OUT_HEIGHT = (1024, 768)
TEX_WIDTH, TEX_HEIGHT = (1024, 1024)


class TestExport(unittest.TestCase):

    def setUp(self):
        pass

    def loadProject(self, filename):
        """load a project"""
        mapSettings = loadProject(filename)

        # extent
        MapExtent(mapSettings.extent().center(),
                  mapSettings.extent().height(),
                  mapSettings.extent().height(), 0).toMapSettings(mapSettings)

        # texture base size
        mapSettings.setOutputSize(QSize(TEX_WIDTH, TEX_HEIGHT))

        return mapSettings

    def test01_export_scene1_webpage(self):
        """test web page export"""

        mapSettings = self.loadProject(dataPath("testproject1.qgs"))

        out_path = outputPath("scene1.html")

        exporter = ThreeJSExporter()
        exporter.loadSettings(dataPath("scene1.qto3settings"))
        exporter.setMapSettings(mapSettings)
        err = exporter.export(out_path)

        assert err, "export failed"

    def test02_export_scene1_webpage_localmode(self):
        """test web page export in local mode"""

        mapSettings = self.loadProject(dataPath("testproject1.qgs"))

        out_path = outputPath("scene1LC.html")

        exporter = ThreeJSExporter()
        exporter.loadSettings(dataPath("scene1.qto3settings"))
        exporter.settings.localMode = exporter.settings.base64 = True

        exporter.setMapSettings(mapSettings)
        err = exporter.export(out_path)

        assert err, "export failed"

    def test03_check_scene1_webpage(self):
        """render exported web page and check page capture"""

        html_path = outputPath("scene1.html")

        url = QUrl.fromLocalFile(html_path)
        url = QUrl(url.toString() + "#cx=-20&cy=34&cz=16&tx=-2&ty=-8&tz=0")

        loop = QEventLoop()
        page = QWebPage()
        page.setViewportSize(QSize(OUT_WIDTH, OUT_HEIGHT))
        page.loadFinished.connect(loop.quit)
        page.mainFrame().setUrl(url)
        loop.exec_()

        page.mainFrame().evaluateJavaScript('document.getElementById("progress").style.display = "none";')

        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(100)
        while page.mainFrame().evaluateJavaScript("app.loadingManager.isLoading"):
            loop.exec_()

        timer.stop()

        image = QImage(OUT_WIDTH, OUT_HEIGHT, QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        page.mainFrame().render(painter)
        painter.end()

        filename = "scene1_qwebpage.png"
        image.save(outputPath(filename))
        assert QImage(outputPath(filename)) == QImage(expectedDataPath(filename)), "captured image is different from expected."

    def test11_export_scene1_image(self):
        """test image export with testproject1.qgs and scene1.qto3settings"""

        mapSettings = self.loadProject(dataPath("testproject1.qgs"))

        filename = "scene1.png"
        out_path = outputPath(filename)

        exporter = ImageExporter()
        exporter.loadSettings(dataPath("scene1.qto3settings"))
        exporter.setMapSettings(mapSettings)
        exporter.initWebPage(OUT_WIDTH, OUT_HEIGHT)

        err = exporter.export(out_path)

        assert not err, err
        assert QImage(out_path) == QImage(expectedDataPath(filename)), "exported image is different from expected."

    def test21_export_scene1_glTF(self):
        """test glTF export with testproject1.qgs and scene1.qto3settings"""

        mapSettings = self.loadProject(dataPath("testproject1.qgs"))

        filename = "scene1.gltf"
        out_path = outputPath(filename)

        exporter = ModelExporter()
        exporter.loadSettings(dataPath("scene1.qto3settings"))
        exporter.setMapSettings(mapSettings)
        exporter.initWebPage(100, 100)

        err = exporter.export(out_path)

        assert not err, err
        assert QFileInfo(out_path).size(), "Empty output file"


if __name__ == "__main__":
    unittest.main()
