# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-16

import os
from qgis.PyQt.QtCore import Qt, QEvent, QEventLoop, QPoint, QTimer
from qgis.PyQt.QtGui import QMouseEvent
from qgis.PyQt.QtWidgets import QDialogButtonBox, QMessageBox, QWidget
from qgis.PyQt.QtTest import QTest
from qgis.core import QgsApplication, QgsProject, QgsRectangle
from qgis.testing import unittest

from Qgis2threejs.core.q3dconst import Script
from Qgis2threejs.tests.utilities import dataPath, initOutputDir
from Qgis2threejs.utils import js_bool, logMessage


WIDTH, HEIGHT = (800, 600)  # view size
UNDEF = "undefined"


def Box3(min, max):
    """min/max: a list containing three coordinate values (x, y, z)"""
    return "new THREE.Box3({}, {})".format(Vec3(*min), Vec3(*max))


def Vec3(x, y, z):
    return "new THREE.Vector3({}, {}, {})".format(x, y, z)


class GUITestBase(unittest.TestCase):

    WND = TREE = None
    DLG = None

    def assertBox3(self, testName, box1, box2=UNDEF):
        self.WND.runScript('assertBox3("{}", {}, {})'.format(testName, box1, box2))

    def assertZRange(self, testName, obj="app.scene", min=UNDEF, max=UNDEF):
        self.WND.runScript('assertZRange("{}", {}, {}, {})'.format(testName, obj, min, max))

    def assertText(self, testName, text, startingElemId=None, partialMatch=False):
        args = '"{}", "{}", {}'.format(testName, text, '"{}"'.format(startingElemId) if startingElemId else UNDEF)

        if partialMatch:
            args += ", true"

        self.WND.runScript('assertText({})'.format(args))

    def assertVisibility(self, testName, elemId, expected=True):
        self.WND.runScript('assertVisibility("{}", "{}", {})'.format(testName, elemId, js_bool(expected)))

    def loadSettings(self, filename):
        self.WND.loadSettings(filename)
        self.sleep(1000)
        self.WND.webPage.loadScriptFile(Script.TEST)

    def mouseClick(self, x, y):
        self.WND.runScript("showMarker({}, {}, 400)".format(x, y))
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


class SceneTest(GUITestBase):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        cls.DLG.close()

    def test01_loadScene1(self):
        self.loadSettings(dataPath("scene1_1.qto3settings"))
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
        layer = cls.WND.iface.settings.getLayer(cls.LAYER_ID)
        if layer is None:
            cls.skipTest("Layer '{}' not found. Skipping test.".format(cls.LAYER_ID))

        if cls.CAMERA_STATE:
            cls.WND.webPage.setCameraState(cls.CAMERA_STATE)

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


# Test result
class JSException(Exception):

    pass


class JSTestException(Exception):

    pass


class GUITestResult(unittest.TestResult):

    DUMMY_TEST = unittest.TestCase()
    VERBOSE = True

    def __init__(self, stream=None, descriptions=None, verbosity=None):
        super().__init__(stream, descriptions, verbosity)

        self.consoleMessages = {}

    def addConsoleMessage(self, message, lineNumber, sourceID):
        if ".py" in sourceID:
            return

        source = "{} ({})".format(sourceID.split("/")[-1], lineNumber)

        if "error" in message.lower():
            e = JSException(source, message)
            self.addError(self.DUMMY_TEST, (type(e), e, e.__traceback__))

        key = "{}: {}".format(source, message)
        self.consoleMessages[key] = self.consoleMessages.get(key, 0) + 1

    def addTestResult(self, testName, result, msg):
        if not result:
            e = JSTestException(testName, msg)
            self.addFailure(self.DUMMY_TEST, (type(e), e, e.__traceback__))

        logMessage("'{}' ({}) {}".format(testName, "success" if result else "err/fail", msg), warning=not result)

    def printResult(self):
        rows = ["", "### Results ###"]
        rows.append("{} tests, {} skipped, {} errors, {} failures".format(self.testsRun, len(self.skipped), len(self.errors), len(self.failures)))

        to_remove = "Qgis2threejs.tests.gui.test_gui."

        if self.skipped:
            rows.append("# Skipped")
            for test, text in self.errors:
                rows.append("* " + text.replace(to_remove, ""))

        if self.errors:
            rows.append("# Errors")
            for test, text in self.errors:
                rows.append("* " + text.replace(to_remove, ""))

        if self.failures:
            rows.append("# Failures")
            for test, text in self.failures:
                rows.append("* " + text.replace(to_remove, ""))

        rows.append("### Console Messages ###")
        for msg, count in self.consoleMessages.items():
            rows.append("* {} [x{}]".format(msg, count))

        rows.append("See web inspector for details.")

        logMessage("\n".join(rows), warning=bool(self.errors or self.failures))

    def startTest(self, test):
        super().startTest(test)

        desc = test.shortDescription() or ""

        if self.VERBOSE:
            logMessage("'{}' {}".format(".".join(test.id().split(".")[-2:]), desc), warning=False)


def runTest(wnd):

    project = QgsProject.instance()
    filename = os.path.basename(project.fileName())

    if filename != "testproject1.qgs":
        QMessageBox.warning(wnd, "Test", "Load 'testproject1.qgs' and retry.")
        return

    initOutputDir()

    # set view size
    wnd.resize(wnd.width() + WIDTH - wnd.ui.webView.width(),
               wnd.height() + HEIGHT - wnd.ui.webView.height())

    # test suite
    testClasses = [SceneTest, PointLayerTest, LineLayerTest, PolygonLayerTest, WidgetTest]
    suite = unittest.TestSuite()

    for testClass in testClasses:
        testClass.WND = wnd
        testClass.TREE = wnd.ui.treeView
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(testClass))

    result = GUITestResult()
    wnd.webPage.bridge.testResultReceived.connect(result.addTestResult)

    # a monkey patch to wnd
    wnd._logToConsole = wnd.logToConsole

    def logToConsole(self, message, lineNumber="", sourceID=""):

        wnd._logToConsole(message, lineNumber, sourceID)

        result.addConsoleMessage(message, lineNumber, sourceID)

    wnd.logToConsole = logToConsole.__get__(wnd)

    # start testing
    logMessage("Testing GUI...")

    try:
        suite(result)

    finally:
        pass

    result.printResult()

    wnd.logToConsole = wnd._logToConsole
