# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-16

from qgis.PyQt.QtCore import QSize
from qgis.testing import unittest

from ..test_utils.unit import start_app, stop_app, logger
from ..test_utils.utils import dataPath, outputPath, loadProject
from ...core.export.export import ThreeJSExporter
from ...core.mapextent import MapExtent
from ...core.plugin.pluginmanager import pluginManager

OUT_WIDTH, OUT_HEIGHT = (1024, 768)
TEX_WIDTH, TEX_HEIGHT = (1024, 1024)


class TestPlugins(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        start_app()

    @classmethod
    def tearDownClass(cls):
        stop_app()

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

        self.assertFalse(err, "export failed")


if __name__ == "__main__":
    unittest.main()
