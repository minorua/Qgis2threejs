# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-27

from qgis.testing import unittest

from .testbase import CLITestBase
from .utils import logger
from ..utils import dataPath


class TestExportWeb(CLITestBase):

    OUT_FILE = "scene1.html"
    LOCAL_MODE = False

    def test01_export_scene1_webpage(self):
        """test web page export"""
        out_path = self.outputPath(self.OUT_FILE)

        self.export_webpage(
            project_path=dataPath(self.PROJ_FILE),
            settings_path=dataPath(self.SETTING_FILE),
            out_path=out_path,
            local_mode=self.LOCAL_MODE
        )

        logger.info(f"exported web page: {out_path}")

    def test02_check_scene1_webpage(self):
        self.check_webpage(self.OUT_FILE)

    def test03_check_scene1_webpage_capture(self):
        self.check_webpage_capture(self.OUT_FILE)


class TestExportWebLocalMode(TestExportWeb):

    OUT_FILE = "scene1.html"
    LOCAL_MODE = True


if __name__ == "__main__":
    unittest.main()
