# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from Qgis2threejs.tests.gui.testbase import LayerTestBase

TEST_DIR = "testproject3"


class TestDEMLayer(LayerTestBase):

    SETTINGS = "scene3_pyramid"
    LAYER_ID = "srtm_62ffafc6_c8b2_4e32_8882_137d6e1bbe4c"

    def test01_showAndZoomToPyramidDEM(self):
        self.loadSettings(TEST_DIR, self.SETTINGS)

        self.zoomTo(self.LAYER_ID)
        self.sleep(2000)

    def test02_zoomFurtherIntoPyramidDEM(self):
        CAMERA_STATE = {
            'lookAt': {'x': -68000, 'y': -80000, 'z': 800},
            'pos': {'x': -95000, 'y': -80000, 'z': 5000}
        }
        self.WND.controller.setCameraState(CAMERA_STATE)
        self.sleep(5000)


class TestDEMLayer_OriginShift(TestDEMLayer):

    SETTINGS = "scene3_pyramid_originshift"
