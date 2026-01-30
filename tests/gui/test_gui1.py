# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialogButtonBox
from qgis.core import QgsRectangle

from Qgis2threejs.tests.gui.testbase import GUITestBase
from Qgis2threejs.tests.test_utils.utils import dataPath


class SceneTest(GUITestBase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        cls.DLG.close()

    def test01_loadScene1(self):
        self.loadSettings(dataPath("testproject1", "scene1_1.qto3settings"))
        self.assertText("Test scene 1", "Test Scene 1", "header", partialMatch=True)

    def test02_ZRange(self):
        # skip if map canvas extent and rotation are not expected status
        mapSettings = self.WND.qgisIface.mapCanvas().mapSettings()
        mapExtent = mapSettings.extent()
        if not mapExtent.contains(QgsRectangle(-30000, -140000, 80000, -50000)) or mapSettings.rotation() != 0:
            self.skipTest("Map canvas extent doesn't contain test area or map is rotated. map: " + mapExtent.toString())

        self.assertZRange("scene z range", min=-4000, max=3776 + 600 * 5)    # min: flat plane, max: pt4 6th feature

    def test10_openScenePDialog(self):
        self.__class__.DLG = self.WND.showScenePropertiesDialog()


class LayerTestBase(GUITestBase):

    LAYER_ID = None
    CAMERA_STATE = None

    @classmethod
    def setUpClass(cls):
        layer = cls.WND.settings.getLayer(cls.LAYER_ID)
        if layer is None:
            raise Exception(f'Layer "{cls.LAYER_ID}" not found.')

        if cls.CAMERA_STATE:
            cls.WND.controller.setCameraState(cls.CAMERA_STATE)

        cls.DLG = cls.WND.showLayerPropertiesDialog(layer)

    @classmethod
    def tearDownClass(cls):
        cls.DLG.close()


class DEMLayerTest(LayerTestBase):

    LAYER_ID = "dem_srtm3020150914165149263"


class VLayerTestBase(LayerTestBase):

    def test01_objectTypes(self):
        """PD: object type combo box test"""
        combo = self.DLG.page.comboBox_ObjectType
        for i in range(combo.count()):
            combo.setCurrentIndex(i)
            self.DLG.ui.buttonBox.button(QDialogButtonBox.StandardButton.Apply).click()
            self.waitBC()


class PointLayerTest(VLayerTestBase):

    LAYER_ID = "pt120150915163204544"
    CAMERA_STATE = {
        'lookAt': {'x': -7420, 'y': -116966, 'z': 0},
        'pos': {'x': -34781, 'y': -143760, 'z': 34119}
    }
    PT4_LAYER_ID = "pt420150915163206372"

    def test02_clickObject(self):
        self.mouseClick(525, 260)   # second feature in pt3 layer (Z=500, h=1000*2)
        self.assertText("clicked coords", " 2500.00", "qr_coords", partialMatch=True)

    def test03_clickObjectWithAttr(self):
        self.mouseClick(485, 160)   # third feature in pt4 layer
        self.assertText("attribute", "cone 3", "qr_attrs_table")

    def test04_hideAndClick(self):
        self.TREE.itemFromLayerId(self.PT4_LAYER_ID).setCheckState(Qt.CheckState.Unchecked)    # hide pt4 layer
        self.waitBC()

        self.mouseClick(485, 160)   # sea
        self.assertText("hide layer", " 0.00", "qr_coords", partialMatch=True)

    def test05_restoreAndClick(self):
        self.TREE.itemFromLayerId(self.PT4_LAYER_ID).setCheckState(Qt.CheckState.Checked)      # show pt4 layer
        self.waitBC()

        self.mouseClick(485, 160)   # third feature in pt4 layer
        self.assertText("show layer", "cone 3", "qr_attrs_table")


class LineLayerTest(VLayerTestBase):

    LAYER_ID = "line120150915163207575"
    CAMERA_STATE = {
        'lookAt': {'x': 40827, 'y': -106069, 'z': 0},
        'pos': {'x': 9037, 'y': -142511, 'z': 24005}
    }
    LINEV_LAYER_ID = "lineV_b839a06f_71fd_4d0d_be1e_a6c9d9e32509"

    def test01_verticalLine(self):
        self.TREE.itemFromLayerId(self.LINEV_LAYER_ID).setCheckState(Qt.CheckState.Checked)    # show lineV layer
        self.waitBC()

        self.assertZRange("scene z range", min=-4000, max=10000)    # min: flat plane, max: lineV


class PolygonLayerTest(VLayerTestBase):

    LAYER_ID = "polygon120150915163203246"
    CAMERA_STATE = {
        'lookAt': {'x': 62558, 'y': -94145, 'z': 0},
        'pos': {'x': 90735, 'y': -127135, 'z': 16134}
    }

    def test06_clickSpace(self):
        self.mouseClick(600, 20)    # sky

        self.assertVisibility("click space", "popup", False)


class WidgetTest(GUITestBase):

    def test01_naviZ(self):
        self.mouseClick(735, 506)   # +Z
        self.sleep(1000)

        self.mouseClick(450, 150)   # sea (dem_srtm30)
        self.assertText("clicked coords", " 0.00", "qr_coords", partialMatch=True)

    def test02_naviX(self):
        self.mouseClick(766, 535)   # +X
        self.sleep(1000)

        self.mouseClick(400, 400)   # flat plane
        self.assertText("clicked coords", " -4000.00", "qr_coords", partialMatch=True)
