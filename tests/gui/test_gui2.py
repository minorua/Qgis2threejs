# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from Qgis2threejs.tests.gui.testbase import GUITestBase, LayerTestBase, Box3


TEST_DIR = "testproject2"


class SceneTest(GUITestBase):

    def test01_loadScene2_1(self):
        self.loadSettings(TEST_DIR, "scene2_1")
        # center of base extent: (450, 350)
        self.assertBox3("Origin shift - On: center of base extent", Box3((-45, -45, 0), (45, 45, 9)))

    def test01_loadScene2_2(self):
        self.loadSettings(TEST_DIR, "scene2_2")
        self.assertBox3("Origin shift - Off: origin of map coordinates", Box3((405, 305, 0), (495, 395, 9)))


class PointLayerTest(LayerTestBase):

    LAYER_ID = "points_230791f1_2e27_4a9d_b5e4_f137f118f216"

    def test01_showLayer(self):
        # current scene: scene2_2
        self.setVisible(True)
        self.assertZRange("points", min=0, max=30)

    def test02_opacityAnimation(self):
        self.WND.ui.animationPanel.playAnimation()
        self.sleep(2000)
        self.setVisible(False)


class LineLayerTest(LayerTestBase):

    LAYER_ID = "linestrings_83a9a52d_c879_42e9_b8cc_984ea053b5cf"

    def test01_showLayer(self):
        # current scene: scene2_2
        self.setVisible(True)
        self.assertZRange("linestrings", min=0, max=50)

    def test02_lineGrowingAnimation(self):
        self.playAnimation()
        self.sleep(2500)

    def test03_loadScene2_1(self):
        self.loadSettings(TEST_DIR, "scene2_1")
        self.setVisible(True)
        self.assertZRange("linestrings", min=0, max=50)

    def test04_lineGrowingAnimation(self):
        self.playAnimation()
        self.sleep(1000 * 4 + 500)
