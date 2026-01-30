# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from Qgis2threejs.tests.gui.testbase import GUITestBase, Box3
from Qgis2threejs.tests.test_utils.utils import dataPath


class SceneTest(GUITestBase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    def test01_loadScene2_1(self):
        self.loadSettings(dataPath("testproject2", "scene2_1.qto3settings"))
        # center of base extent: (450, 350)
        self.assertBox3("Origin shift - On: center of base extent", Box3((-45, -45, 0), (45, 45, 9)))

    def test01_loadScene2_2(self):
        self.loadSettings(dataPath("testproject2", "scene2_2.qto3settings"))
        self.assertBox3("Origin shift - Off: origin of map coordinates", Box3((405, 305, 0), (495, 395, 9)))
