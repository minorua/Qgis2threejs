# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-16

from qgis.PyQt.QtCore import QSize
from qgis.testing import unittest

from Qgis2threejs.export import ThreeJSExporter
from Qgis2threejs.mapextent import MapExtent
from Qgis2threejs.pluginmanager import pluginManager
from Qgis2threejs.tests.utilities import dataPath, outputPath, loadProject

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
        exporter.settings.localMode = exporter.settings.jsonSerializable = True

        exporter.setMapSettings(mapSettings)
        err = exporter.export(out_path)

        assert err, "export failed"


if __name__ == "__main__":
    unittest.main()
