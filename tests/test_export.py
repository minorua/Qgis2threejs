# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2018-11-27

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
import os
from PyQt5.QtCore import QFileInfo, QSize
from PyQt5.QtGui import QImage
from qgis.core import QgsCoordinateReferenceSystem, QgsMapSettings, QgsRectangle
from qgis.testing import start_app, unittest

from Qgis2threejs.export import ThreeJSExporter, ImageExporter, ModelExporter
from Qgis2threejs.q3dcontroller import Q3DController
from Qgis2threejs.rotatedrect import RotatedRect
from Qgis2threejs.tests.utilities import dataPath, expectedDataPath, outputPath, loadProject

QGISAPP = start_app()


class TestImageExport(unittest.TestCase):

  def setUp(self):
    pass

  def loadProject(self, filename):
    """load a project"""
    TEX_WIDTH, TEX_HEIGHT = (1024, 1024)

    mapSettings = loadProject(filename)

    # extent
    RotatedRect(mapSettings.extent().center(),
                mapSettings.extent().height(),
                mapSettings.extent().height(), 0).toMapSettings(mapSettings)

    # texture base size
    mapSettings.setOutputSize(QSize(TEX_WIDTH, TEX_HEIGHT))

    return mapSettings

  def test01_export_scene1_webpage(self):
    """test web page export with testproject1.qgs and scene1.qto3settings"""

    mapSettings = self.loadProject(dataPath("testproject1.qgs"))

    out_path = outputPath("scene1.html")

    exporter = ThreeJSExporter()
    exporter.loadSettings(dataPath("scene1.qto3settings"))
    exporter.setMapSettings(mapSettings)
    err = exporter.export(out_path)

    assert not err, err

  def test02_export_scene1_image(self):
    """test image export with testproject1.qgs and scene1.qto3settings"""

    OUT_WIDTH, OUT_HEIGHT = (1024, 768)

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

  def test03_export_scene1_glTF(self):
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
