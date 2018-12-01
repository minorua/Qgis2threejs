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

  def createController(self, project_path, settings_path):
    """load a project and export settings, and create a controller"""
    TEX_WIDTH, TEX_HEIGHT = (1024, 1024)

    # load a test project
    mapSettings = loadProject(project_path)

    # viewer controller
    controller = Q3DController()
    controller.settings.loadSettingsFromFile(settings_path)
    controller.settings.updateLayerList()

    # extent
    RotatedRect(mapSettings.extent().center(),
                mapSettings.extent().height(),
                mapSettings.extent().height(), 0).toMapSettings(mapSettings)

    # texture size
    mapSettings.setOutputSize(QSize(TEX_WIDTH, TEX_HEIGHT))
    controller.settings.setMapSettings(mapSettings)
    return controller

  def test01_export_scene1_webpage(self):
    """test web page export with testproject1.qgs and scene1.qto3settings"""

    controller = self.createController(dataPath("testproject1.qgs"), dataPath("scene1.qto3settings"))

    out_path = outputPath("scene1.html")

    exporter = ThreeJSExporter(controller.settings)
    err = exporter.export(out_path)

    assert not err, err

  def test02_export_scene1_image(self):
    """test image export with testproject1.qgs and scene1.qto3settings"""

    OUT_WIDTH, OUT_HEIGHT = (1024, 768)

    controller = self.createController(dataPath("testproject1.qgs"), dataPath("scene1.qto3settings"))

    filename = "scene1.png"
    out_path = outputPath(filename)

    exporter = ImageExporter(controller)
    exporter.initWebPage(OUT_WIDTH, OUT_HEIGHT)
    err = exporter.export(out_path)

    assert not err, err
    assert QImage(out_path) == QImage(expectedDataPath(filename)), "exported image is different from expected."

  def test03_export_scene1_glTF(self):
    """test glTF export with testproject1.qgs and scene1.qto3settings"""

    controller = self.createController(dataPath("testproject1.qgs"), dataPath("scene1.qto3settings"))

    filename = "scene1.gltf"
    out_path = outputPath(filename)

    exporter = ModelExporter(controller)
    exporter.initWebPage(100, 100)
    err = exporter.export(out_path)

    assert not err, err
    assert QFileInfo(out_path).size(), "Empty output file"


if __name__ == "__main__":
  unittest.main()
