# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-27

import os

from qgis.testing import unittest

from .testbase import CLITestBase   # Enable test mode before importing plugin's other modules
from .utils import logger
from ..utils import dataPath


class TestExportWeb(CLITestBase):

    PROJ_FILE = "testproject2/testproject2.qgs"
    SETTING_FILE = "testproject2/scene2_g2.qto3settings"
    LOCAL_MODE = False
    TEMPLATE = "3DViewer.html"
    OUT_FILE = "scene1.html"

    def test01_export_scene1_webpage(self):
        """test web page export"""
        out_path = self.outputPath(self.OUT_FILE)

        self.export_webpage(
            project_path=dataPath(self.PROJ_FILE),
            settings_path=dataPath(self.SETTING_FILE),
            out_path=out_path,
            local_mode=self.LOCAL_MODE,
            template=self.TEMPLATE
        )

        self.assertTrue(os.path.exists(out_path), "Failed to export.")
        logger.info(f"Web page exported: {out_path}")

        logger.info(f"Checking web page: {out_path}")
        self.check_webpage(out_path)


class TestExportWeb_datgui(TestExportWeb):

    SETTING_FILE = "testproject2/scene2_datgui.qto3settings"
    TEMPLATE = "3DViewer(dat-gui).html"

    def check_webpage(self, filename):
        checker =  super().check_webpage(filename)

        # Check item counts in the dat-gui panel
        panel = "__qgis2threejs.gui.dat.panel"
        layers = f"{panel}.__folders['Layers']"
        cp = f"{panel}.__folders['Custom Plane']"

        self.assertEqual(checker.runScript(f"{panel}.__controllers.length"),           1, "top level item count not expected.")
        self.assertEqual(checker.runScript(f"Object.keys({panel}.__folders).length"),  3, "top level folder count not expected.")
        self.assertEqual(checker.runScript(f"Object.keys({layers}.__folders).length"), 3, "layer count not expected.")
        self.assertEqual(checker.runScript(f"{cp}.__controllers.length"),              4, "custom plane item count not expected.")
        return checker


if __name__ == "__main__":
    unittest.main()
