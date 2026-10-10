# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import Qt, QEventLoop, QTimer
from qgis.PyQt.QtTest import QSignalSpy
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
        cls.WND.showStatusMessage(f"{cls.__name__}: Test started.", 3000)

        if cls.CAMERA_STATE:
            cls.WND.controller.setCameraState(cls.CAMERA_STATE)

        cls.WND.webPage.loadScriptFile(ScriptFile.TEST, wait=True)

    @classmethod
    def tearDownClass(cls):
        cls.runScript("gui.popup.hide()")
        cls.setLabels()
        cls.WND.showStatusMessage(f"{cls.__name__}: Test finished.", 3000)
        super().tearDownClass()

    @classmethod
    def runScript(cls, script):
        cls.WND.runScript(script, wait=True)

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
        cls.runScript(f"emulateClick({x}, {y})")
        cls.sleep(500)

    @classmethod
    def keyPress(cls, key, code):
        cls.runScript(f'emulateKeyPress("{key}", "{code}")')
        cls.sleep(200)

    @classmethod
    def setLabels(cls, header="", footer=""):
       cls.WND.controller.updateWidget("Label", {
            "Header": header,
            "Footer": footer
        })

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

    def playAnimation(self, timeout=5000):
        spy = QSignalSpy(self.WND.webPage.bridge.animationStopped)

        self.updateTestLabels(animating=True)
        self.WND.ui.animationPanel.playAnimation()

        self.assertTrue(spy.wait(timeout), "Timed out waiting for animation to finish.")
        self.updateTestLabels(animating=False)

    def updateTestLabels(self, animating=False):
        testname = self.id().split(".")[-1]
        desc = self.shortDescription() or ""
        if animating:
            desc += "<br>Animation in progress..."

        self.setLabels(f"{self.__class__.__name__} - {testname}", desc)

    def loadSettings(self, testDir, filename, useTestLabels=True):
        if not filename.endswith(".qto3settings"):
            filename += ".qto3settings"
        filename = dataPath(testDir, filename)

        spy = QSignalSpy(self.WND.webPage.bridge.sceneLoaded)

        self.WND.loadSettings(filename)     # this reloads the page

        self.assertTrue(spy.wait(), "Time out while loading settings and scene.")

        if useTestLabels:
            self.updateTestLabels()

        # Load test script after the page finishes loading.
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
    def setVisible(cls, visible, layerId=None):
        cls.TREE.itemFromLayerId(layerId if layerId else cls.LAYER_ID).setCheckState(Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked)
        cls.sleep(400)  # TODO

    @classmethod
    def zoomTo(cls, layerId=None):
        cls.WND.controller.zoomToLayer(cls.WND.settings.getLayer(layerId if layerId else cls.LAYER_ID))
        cls.sleep(400)
