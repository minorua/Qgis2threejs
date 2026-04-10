# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-27

from qgis.testing import unittest

from .testbase import CLITestBase
from .utils import logger
from ..utils import dataPath


class TestExportWeb(CLITestBase):

    LOCAL_MODE = False
    TEMPLATE = "3DViewer.html"

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

        logger.info(f"exported web page: {out_path}")

    def test02_check_scene1_webpage(self):
        self.check_webpage(self.OUT_FILE)

    def test03_check_scene1_webpage_capture(self):
        self.check_webpage_capture(self.OUT_FILE)


class TestExportWebLocalMode(TestExportWeb):

    LOCAL_MODE = True


class TestExportWebLM_datgui(TestExportWebLocalMode):

    TEMPLATE = "3DViewer(dat-gui).html"

    def check_webpage(self, filename):
        wpv =  super().check_webpage(filename)

        panel = "Q3D.gui.dat.gui"
        layers = f"{panel}.__folders['Layers']"
        cp = f"{panel}.__folders['Custom Plane']"

        self.assertEqual(wpv.runScript(f"{panel}.__controllers.length"),            1, "top level item count not expected.")
        self.assertEqual(wpv.runScript(f"Object.keys({panel}.__folders).length"),   2, "top level folder count not expected.")
        self.assertEqual(wpv.runScript(f"Object.keys({layers}.__folders).length"), 15, "layer count not expected.")
        self.assertEqual(wpv.runScript(f"{cp}.__controllers.length"),               6, "custom plane item count not expected.")   # A slider has two controllers.
        return wpv


class TestExportWebLM_Mobile(TestExportWebLocalMode):

    TEMPLATE = "Mobile.html"


if __name__ == "__main__":
    unittest.main()
