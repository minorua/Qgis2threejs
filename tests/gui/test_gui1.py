# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialogButtonBox
from qgis.core import QgsRectangle

from Qgis2threejs.tests.gui.testbase import GUITestBase, LayerTestBase


TEST_DIR = "testproject1"


class SceneTest(GUITestBase):

    def test01_loadScene1(self):
        self.loadSettings(TEST_DIR, "scene1_1")
        self.assertText("Test scene 1", "Test Scene 1", "header", partialMatch=True)

    def test02_ZRange(self):
        # skip if map canvas extent and rotation are not expected status
        mapSettings = self.WND.qgisIface.mapCanvas().mapSettings()
        mapExtent = mapSettings.extent()
        if not mapExtent.contains(QgsRectangle(-30000, -140000, 80000, -50000)) or mapSettings.rotation() != 0:
            self.skipTest("Map canvas extent doesn't contain test area or map is rotated. map: " + mapExtent.toString())

        self.assertZRange("scene z range", min=-4000, max=3776 + 600 * 5)    # min: flat plane, max: pt4 6th feature

    def test10_openScenePDialog(self):
        dlg = self.WND.showScenePropertiesDialog()
        for i in range(dlg.page.tabWidget.count()):
            dlg.page.tabWidget.setCurrentIndex(i)
            self.sleep(1000)
        dlg.close()


class LayerDialogTestBase(LayerTestBase):

    def test01_propertiesdialog(self):
        dlg = self.showDialog()
        for i in range(dlg.page.tabWidget.count()):
            dlg.page.tabWidget.setCurrentIndex(i)
            self.sleep(750)

        dlg.close()

    def showDialog(self):
        return self.WND.showLayerPropertiesDialog(self.LAYER)


class DEMLayerTest(LayerDialogTestBase):

    LAYER_ID = "dem_srtm3020150914165149263"


class VLayerTestBase(LayerDialogTestBase):

    def test01_propertiesdialog(self):
        super().test01_propertiesdialog()

        dlg = self.showDialog()
        combo = dlg.page.comboBox_ObjectType
        for i in reversed(range(combo.count())):
            combo.setCurrentIndex(i)
            dlg.ui.buttonBox.button(QDialogButtonBox.StandardButton.Apply).click()
            self.waitBC()

        dlg.close()


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
        self.setVisible(False, self.PT4_LAYER_ID)

        self.mouseClick(485, 160)   # sea
        self.assertText("hide layer", " 0.00", "qr_coords", partialMatch=True)

    def test05_restoreAndClick(self):
        self.setVisible(True, self.PT4_LAYER_ID)

        self.mouseClick(485, 160)   # third feature in pt4 layer
        self.assertText("show layer", "cone 3", "qr_attrs_table")


class LineLayerTest(VLayerTestBase):

    LAYER_ID = "line120150915163207575"
    CAMERA_STATE = {
        'lookAt': {'x': 40827, 'y': -106069, 'z': 0},
        'pos': {'x': 9037, 'y': -142511, 'z': 24005}
    }
    LINEV_LAYER_ID = "lineV_b839a06f_71fd_4d0d_be1e_a6c9d9e32509"

    def test02_verticalLine(self):
        self.setVisible(True, self.LINEV_LAYER_ID)

        self.assertZRange("scene z range", min=-4000, max=10000)    # min: flat plane, max: lineV


class PolygonLayerTest(VLayerTestBase):

    LAYER_ID = "polygon120150915163203246"
    CAMERA_STATE = {
        'lookAt': {'x': 62558, 'y': -94145, 'z': 0},
        'pos': {'x': 90735, 'y': -127135, 'z': 16134}
    }

    def test02_clickSpace(self):
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


class KeyboardInteractionTest(GUITestBase):

    CAMERA_STATE = {
        'lookAt': {'x': -4534, 'y': -136988, 'z': 0},
        'pos': {'x': -55233, 'y': -195106, 'z': 37283}
    }

    def test01_hideLabels(self):
        self.sleep(500)
        self.keyPress(Qt.Key_L)

    def test02_showLabels(self):
        self.sleep(500)
        self.keyPress(Qt.Key_L)


class CameraAnimationTest(GUITestBase):

    def test01_cameraAnimation(self):
        self.playAnimation()
        self.sleep(8000 + 500)
