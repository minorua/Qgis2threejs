# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from Qgis2threejs.tests.gui.testbase import GUITestBase, LayerTestBase, Box3


TEST_DIR = "testproject2"


class SceneTest(GUITestBase):

    def test01_loadScene2_1(self):
        self.loadSettings(TEST_DIR, "scene2_1")
        # Center of Base Extent: (450, 350)
        self.assertBox3("Origin shift - On: center of base extent", Box3((-45, -45, 0), (45, 45, 9)))

    def test02_loadScene2_2(self):
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

    def test01_loadScene2_1(self):
        """Line"""
        self.loadSettings(TEST_DIR, "scene2_1")
        self.setVisible(True)
        self.assertZRange("linestrings", min=0, max=50)

    def test02_lineGrowingAnimation(self):
        self.playAnimation()
        self.sleep(1000 * 4 + 500)

    def test03_loadScene2_2(self):
        """Thick line"""
        self.loadSettings(TEST_DIR, "scene2_2")
        self.setVisible(True)
        self.assertZRange("linestrings", min=0, max=50)

    def test04_lineGrowingAnimation(self):
        self.playAnimation()
        self.sleep(2500)


class PointCloudLayerTest(LayerTestBase):

    LAYER_ID = "pointcloud_d87d4a8e_453c_4f82_8cf9_ef2a3d340be4"
    # BBOX: (300.46, 300.32, 0) - (399.97, 399.94, 49.89)

    def test01_loadScene2_1(self):
        self.loadSettings(TEST_DIR, "scene2_1")
        # Center of Base Extent: (450, 350)
        # BBOX: (-45, -45, 0) - (45, 45, 9)
        self.setVisible(True)
        self.sleep(3000)

        self.assertBox3("Point cloud with origin shift", Box3((-149.54, -49.68, 0), (45, 49.94, 49.89)), precision=4)

    def test02_loadScene2_2(self):
        self.loadSettings(TEST_DIR, "scene2_2")
        # BBOX: (405, 305, 0) - (495, 395, 9)
        self.setVisible(True)
        self.sleep(3000)

        self.assertBox3("Point cloud without origin shift", Box3((300.46, 300.32, 0), (495, 399.94, 49.89)), precision=4)
