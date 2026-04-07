# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-16

from qgis.testing import unittest

from .testbase import CLITestBase
from .utils import start_app, stop_app, loadProject
from ..utils import dataPath, outputPath
from ...core.export.export import ThreeJSExporter
from ...core.plugin.pluginmanager import pluginManager


class TestPlugins(unittest.TestCase, CLITestBase):

    SETTING_FILE = "testproject1/gsielevtile.qto3settings"

    @classmethod
    def setUpClass(cls):
        start_app()

    @classmethod
    def tearDownClass(cls):
        stop_app()

    def setUp(self):
        pluginManager(True)   # enables all plugins

    def test01_gsielevtile(self):
        """test exporting with GSI elevation tile plugin"""
        mapSettings = loadProject(dataPath(self.PROJ_FILE))

        out_path = outputPath("scene1_gsielevtile.html")

        exporter = ThreeJSExporter()
        exporter.loadSettings(dataPath(self.SETTING_FILE))
        exporter.settings.localMode = exporter.settings.requiresJsonSerializable = True

        exporter.setMapSettings(mapSettings)
        exporter.export(out_path)


if __name__ == "__main__":
    unittest.main()
