# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2015-09-14

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
# TODO: version >= 2.4
import os
from unittest import TestCase
from PyQt4.QtCore import QSize
from qgis.core import QgsCoordinateReferenceSystem, QgsMapSettings, QgsRectangle

from Qgis2threejs.api import Exporter
from utilities import dataPath, outputPath, loadProject


class TestApi(TestCase):

  def setUp(self):
    pass

  def test01_export_empty(self):
    """test exporting with empty export settings"""
    # map settings
    canvasSize = QSize(600, 600)
    width = 1000.
    height = width * canvasSize.height() / canvasSize.width()
    crs = QgsCoordinateReferenceSystem(3099, QgsCoordinateReferenceSystem.EpsgCrsId)  # JGD2000 / UTM zone 53N

    mapSettings = QgsMapSettings()
    mapSettings.setOutputSize(canvasSize)
    mapSettings.setExtent(QgsRectangle(0, 0, width, height))
    mapSettings.setDestinationCrs(crs)

    exporter = Exporter()
    exporter.setMapSettings(mapSettings)
    err = exporter.export(outputPath(os.path.join("empty", "empty.html")))
    assert err == Exporter.NO_ERROR, err

  def test02_export_project1(self):
    """test exporting from a test project"""
    projectPath = dataPath("testproject1.qgs")
    mapSettings = loadProject(projectPath)

    # output size
    width = 800
    height = width * mapSettings.extent().height() / mapSettings.extent().width()
    mapSettings.setOutputSize(QSize(width, height))

    exporter = Exporter(None, dataPath("testproject1.qto3settings"))
    exporter.settings.setMapSettings(mapSettings)
    err = exporter.export(outputPath(os.path.join("testproject1", "testproject1.html")))
    assert err == Exporter.NO_ERROR, err

if __name__ == "__main__":
  import unittest
  unittest.main()
