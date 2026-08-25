# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import Qt, QEvent, QEventLoop, QPoint, QPointF, QTimer
from qgis.PyQt.QtGui import QKeyEvent
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtTest import QTest
from qgis.core import QgsApplication
from qgis.testing import unittest

from Qgis2threejs.core.const import ScriptFile
from Qgis2threejs.utils.js import js_bool
from Qgis2threejs.tests.utils import dataPath


UNDEF = "undefined"


def Box3(min, max):
    """min/max: a list containing three coordinate values (x, y, z)"""
    return f"new THREE.Box3({Vec3(*min)}, {Vec3(*max)})"


def Vec3(x, y, z):
    return f"new THREE.Vector3({x}, {y}, {z})"


class GUITestBase(unittest.TestCase):

    WND = TREE = None
    CAMERA_STATE = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        if cls.CAMERA_STATE:
            cls.WND.controller.setCameraState(cls.CAMERA_STATE)

    @classmethod
    def tearDownClass(cls):
        cls.runScript("gui.popup.hide()")
        super().tearDownClass()

    @classmethod
    def runScript(cls, script):
        cls.WND.runScript(script)

    @classmethod
    def playAnimation(cls):
        cls.WND.ui.animationPanel.playAnimation()

    @classmethod
    def assertBox3(cls, testName, box1, box2=UNDEF, precision=UNDEF):
        cls.runScript(f'assertBox3("{testName}", {box1}, {box2}, {precision})')

    @classmethod
    def assertZRange(cls, testName, obj="app.scene", min=UNDEF, max=UNDEF, precision=UNDEF):
        cls.runScript(f'assertZRange("{testName}", {obj}, {min}, {max}, {precision})')

    @classmethod
    def assertText(cls, testName, text, startingElemId=None, partialMatch=False):
        startingElemId = f'"{startingElemId}"' if startingElemId else UNDEF
        cls.runScript(f'assertText("{testName}", "{text}", {startingElemId}, {js_bool(partialMatch)})')

    @classmethod
    def assertVisibility(cls, testName, elemId, expected=True):
        cls.runScript(f'assertVisibility("{testName}", "{elemId}", {js_bool(expected)})')

    @classmethod
    def mouseClick(cls, x, y):
        cls.runScript(f"showMarker({x}, {y}, 400)")
        cls.sleep(300)
        cls.runScript(f"emulateClick({x}, {y})")
        cls.sleep(500)

    @classmethod
    def keyPress(cls, key, code):
        cls.runScript(f'emulateKeyPress("{key}", "{code}")')
        cls.sleep(200)

    @staticmethod
    def sleep(msec=500):
        loop = QEventLoop()
        QTimer.singleShot(msec, loop.quit)
        loop.exec()

    @staticmethod
    def doEvents():
        GUITestBase.sleep(1)

    def setUp(self):
        self.updateTestLabels()

    def tearDown(self):
        self.sleep()

    def updateTestLabels(self):
        testname = self.id().split(".")[-1]
        desc = self.shortDescription() or ""
        if testname.endswith("Animation"):
            desc += "<br>Animation Running..."

        self.WND.controller.updateWidget("Label", {
            "Header": f"{self.__class__.__name__} - {testname}",
            "Footer": desc
        })

    def loadSettings(self, testDir, filename, useTestLabels=True):
        loop = QEventLoop()
        self.WND.webPage.bridge.sceneLoaded.connect(loop.quit)

        if not filename.endswith(".qto3settings"):
            filename += ".qto3settings"
        filename = dataPath(testDir, filename)

        self.WND.loadSettings(filename)     # page will be reloaded

        loop.exec()

        if useTestLabels:
            self.updateTestLabels()

        # load test script after page is loaded
        self.WND.webPage.loadScriptFile(ScriptFile.TEST, wait=True)


class LayerTestBase(GUITestBase):

    LAYER_ID = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.LAYER = cls.WND.settings.getLayer(cls.LAYER_ID)
        if cls.LAYER is None:
            raise Exception(f'Layer "{cls.LAYER_ID}" not found.')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

    @classmethod
    def waitBC(cls):
        """wait for build to complete"""
        cls.sleep(400)

    @classmethod
    def setVisible(cls, visible, layerId=None):
        cls.TREE.itemFromLayerId(layerId if layerId else cls.LAYER_ID).setCheckState(Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked)
        cls.waitBC()
