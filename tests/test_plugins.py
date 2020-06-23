# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2015-09-16

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
from PyQt5.QtCore import QSize
from qgis.testing import unittest

from Qgis2threejs.export import ThreeJSExporter
from Qgis2threejs.mapextent import MapExtent
from Qgis2threejs.pluginmanager import pluginManager
from .utilities import dataPath, outputPath, loadProject

OUT_WIDTH, OUT_HEIGHT = (1024, 768)
TEX_WIDTH, TEX_HEIGHT = (1024, 1024)


class TestPlugins(unittest.TestCase):

    def setUp(self):
        pluginManager(True)   # enables all plugins

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

    def test01_gsielevtile(self):
        """test exporting with GSI elevation tile plugin"""
        mapSettings = self.loadProject(dataPath("testproject1.qgs"))

        out_path = outputPath("scene1_gsielevtile.html")

        exporter = ThreeJSExporter()
        exporter.loadSettings(dataPath("gsielevtile.qto3settings"))
        exporter.settings.localMode = exporter.settings.base64 = True

        exporter.setMapSettings(mapSettings)
        err = exporter.export(out_path)

        assert err, "export failed"


if __name__ == "__main__":
    unittest.main()
