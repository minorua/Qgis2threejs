# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox
from qgis.core import QgsProject
from qgis.testing import unittest

from Qgis2threejs.tests.test_utils.utils import initOutputDir
from Qgis2threejs.utils import logger

WIDTH, HEIGHT = (800, 600)  # view size


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
        """Currently not used.
            TODO: fetch console messages from web page."""

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

        m = "'{}' ({}) {}".format(testName, "success" if result else "err/fail", msg)
        if result:
            logger.info(m)
        else:
            logger.warning(m)

    def printResult(self):
        rows = ["", "### Results ###"]
        rows.append(f"{self.testsRun} tests, {len(self.skipped)} skipped, {len(self.errors)} errors, {len(self.failures)} failures")

        to_remove = "Qgis2threejs.tests.gui.test_gui."

        if self.skipped:
            rows.append("# Skipped")
            for _test, text in self.errors:
                rows.append("* " + text.replace(to_remove, ""))

        if self.errors:
            rows.append("# Errors")
            for _test, text in self.errors:
                rows.append("* " + text.replace(to_remove, ""))

        if self.failures:
            rows.append("# Failures")
            for _test, text in self.failures:
                rows.append("* " + text.replace(to_remove, ""))

        rows.append("### Console Messages ###")
        # for msg, count in self.consoleMessages.items():
        #    rows.append("* {} [x{}]".format(msg, count))

        rows.append("See web inspector for details.")

        if self.errors or self.failures:
            logger.error("\n".join(rows))
        else:
            logger.info("\n".join(rows))

    def startTest(self, test):
        super().startTest(test)

        desc = test.shortDescription() or ""

        if self.VERBOSE:
            logger.info("'{}' {}".format(".".join(test.id().split(".")[-2:]), desc))


def runTest(wnd):
    filename = os.path.basename(QgsProject.instance().fileName())

    if "testproject" not in filename:
        QMessageBox.warning(wnd, "Test", 'Load one of "testproject?.qgs" and retry.')
        return

    initOutputDir()

    # set view size
    wnd.resize(wnd.width() + WIDTH - wnd.ui.webView.width(),
               wnd.height() + HEIGHT - wnd.ui.webView.height())

    # test suite
    if filename == "testproject1.qgs":
        from .test_gui1 import SceneTest, DEMLayerTest, PointLayerTest, LineLayerTest, PolygonLayerTest, WidgetTest, KeyboardInteractionTest, CameraAnimationTest
        testClasses = [SceneTest, DEMLayerTest, PointLayerTest, LineLayerTest, PolygonLayerTest, WidgetTest, KeyboardInteractionTest, CameraAnimationTest]

    elif filename == "testproject2.qgs":
        from .test_gui2 import SceneTest, PointLayerTest, LineLayerTest, PointCloudLayerTest
        testClasses = [SceneTest, PointLayerTest, LineLayerTest, PointCloudLayerTest]

    else:
        testClasses = []

    lines = ["Enter test numbers to run (comma-separated allowed):\n"]
    lines.append("0: Run all tests\n")

    for i, cls in enumerate(testClasses, start=1):
        lines.append(f"{i}: {cls.__name__}")

    message = "\n".join(lines)

    text, ok = QInputDialog.getText(wnd, "Select tests", message, text="0")
    text = text.strip()
    if not ok or not text:
        return

    if text != "0":
        try:
            selected = []
            for idx in [int(x) for x in text.split(",")]:
                if 1 <= idx <= len(testClasses):
                    selected.append(testClasses[idx - 1])

            testClasses = selected

        except ValueError:
            QMessageBox.error(wnd, "Test", f"Invalid input: {text}")
            return

    suite = unittest.TestSuite()
    for testClass in testClasses:
        testClass.WND = wnd
        testClass.TREE = wnd.ui.treeView
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(testClass))

    result = GUITestResult()
    wnd.webPage.bridge.testResultReceived.connect(result.addTestResult)

    logger.info(f"Testing GUI using {filename}...")
    try:
        suite(result)
    finally:
        pass

    result.printResult()
