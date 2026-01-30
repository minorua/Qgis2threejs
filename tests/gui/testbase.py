# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import Qt, QEvent, QEventLoop, QPoint, QTimer
from qgis.PyQt.QtGui import QMouseEvent
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtTest import QTest
from qgis.core import QgsApplication
from qgis.testing import unittest

from Qgis2threejs.core.const import ScriptFile
from Qgis2threejs.utils import js_bool


UNDEF = "undefined"


def Box3(min, max):
    """min/max: a list containing three coordinate values (x, y, z)"""
    return f"new THREE.Box3({Vec3(*min)}, {Vec3(*max)})"


def Vec3(x, y, z):
    return f"new THREE.Vector3({x}, {y}, {z})"


class GUITestBase(unittest.TestCase):

    WND = TREE = None
    DLG = None

    def assertBox3(self, testName, box1, box2=UNDEF):
        self.WND.runScript(f'assertBox3("{testName}", {box1}, {box2})')

    def assertZRange(self, testName, obj="app.scene", min=UNDEF, max=UNDEF):
        self.WND.runScript(f'assertZRange("{testName}", {obj}, {min}, {max})')

    def assertText(self, testName, text, startingElemId=None, partialMatch=False):
        startingElemId = f'"{startingElemId}"' if startingElemId else UNDEF
        self.WND.runScript(f'assertText("{testName}", "{text}", {startingElemId}, {js_bool(partialMatch)})')

    def assertVisibility(self, testName, elemId, expected=True):
        self.WND.runScript(f'assertVisibility("{testName}", "{elemId}", {js_bool(expected)})')

    def loadSettings(self, filename):
        loop = QEventLoop()
        self.WND.webPage.bridge.sceneLoaded.connect(loop.quit)

        self.WND.loadSettings(filename)     # page will be reloaded

        loop.exec()

        # load test script after page is loaded
        self.WND.webPage.loadScriptFile(ScriptFile.TEST, wait=True)

    def mouseClick(self, x, y):
        self.WND.runScript(f"showMarker({x}, {y}, 400)")
        self.sleep(500)

        pos = QPoint(x, y)
        w = self.WND.ui.webView

        if w._page.isWebEnginePage:
            w = w.findChild(QWidget)
            press = QMouseEvent(QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
            release = QMouseEvent(QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)

            QgsApplication.postEvent(w, press)
            QgsApplication.postEvent(w, release)
        else:
            QTest.mouseClick(w, Qt.MouseButton.LeftButton, pos=pos)

        self.sleep(100)

    @classmethod
    def sleep(cls, msec=500):
        loop = QEventLoop()
        QTimer.singleShot(msec, loop.quit)
        loop.exec()

    @classmethod
    def doEvents(cls):
        cls.sleep(1)

    @classmethod
    def waitBC(cls):
        """wait for build to complete"""
        cls.sleep(400)

    def tearDown(self):
        self.sleep()
