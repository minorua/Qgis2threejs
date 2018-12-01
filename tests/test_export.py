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
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QImage
from qgis.core import QgsCoordinateReferenceSystem, QgsMapSettings, QgsRectangle
from qgis.testing import start_app, unittest

from Qgis2threejs.export import ImageExporter
from Qgis2threejs.q3dviewercontroller import Q3DViewerController
from Qgis2threejs.rotatedrect import RotatedRect
from Qgis2threejs.tests.utilities import dataPath, expectedDataPath, outputPath, loadProject

QGISAPP = start_app()


class TestImageExport(unittest.TestCase):

  def setUp(self):
    pass

  def test01_export_scene1(self):
    """test image export with testproject1.qgs and scene1.qto3settings"""

    OUT_WIDTH, OUT_HEIGHT = (1024, 768)
    TEX_WIDTH, TEX_HEIGHT = (1024, 1024)

    # load a test project
    mapSettings = loadProject(dataPath("testproject1.qgs"))

    # viewer controller
    controller = Q3DViewerController()
    controller.settings.loadSettingsFromFile(dataPath("scene1.qto3settings"))
    controller.settings.updateLayerList()

    # create an exporter
    exporter = ImageExporter(controller)
    exporter.initWebPage(OUT_WIDTH, OUT_HEIGHT)

    # extent
    RotatedRect(mapSettings.extent().center(),
                mapSettings.extent().height(),
                mapSettings.extent().height(), 0).toMapSettings(mapSettings)

    # texture size
    mapSettings.setOutputSize(QSize(TEX_WIDTH, TEX_HEIGHT))
    controller.settings.setMapSettings(mapSettings)

    # export
    filename = "scene1.png"
    err = exporter.export(outputPath(filename))

    assert not err, err
    assert QImage(outputPath(filename)) == QImage(expectedDataPath(filename)), "exported image is different from expected."


if __name__ == "__main__":
  unittest.main()
