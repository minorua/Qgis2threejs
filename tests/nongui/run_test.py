# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-06

import os
import sys
import traceback
from qgis.testing import unittest

# Python path setting
plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
plugins_dir = os.path.dirname(plugin_dir)
sys.path.append(plugins_dir)

# configuration for testing
from Qgis2threejs import conf
conf.TESTING = True

logger = None


class LoggingTestResult(unittest.TextTestResult):
    """A test result class that logs test results using the logger."""

    def startTest(self, test):
        super().startTest(test)
        logger.info("")
        logger.info(f"[START] {test.id()}")

    def addSuccess(self, test):
        super().addSuccess(test)
        logger.info(f"[SUCCESS] {test.id()}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        logger.error(f"[FAILURE] {test.id()}\n{'-' * 70}\n{''.join(traceback.format_exception(*err))}\n{'-' * 70}")

    def addError(self, test, err):
        super().addError(test, err)
        logger.error(f"[ERROR] {test.id()}\n{'-' * 70}\n{''.join(traceback.format_exception(*err))}\n{'-' * 70}")


def runTest(debug_mode=None):
    global logger

    if debug_mode is not None:
        conf.DEBUG_MODE = debug_mode

    # import logger after setting DEBUG_MODE
    from Qgis2threejs.utils import logger as _logger

    logger = _logger
    logger.info(f"DEBUG_MODE: {conf.DEBUG_MODE}")
    logger.info("Starting tests...")

    # initialize output directory
    from Qgis2threejs.tests.utils import initOutputDir, outputPath
    initOutputDir()

    logger.info(f"Plugin Dir.: {plugin_dir}")
    logger.info(f"Output Dir.: {outputPath()}")

    # run tests
    suite = unittest.TestLoader().discover("Qgis2threejs.tests.nongui")
    result = unittest.TextTestRunner(resultclass=LoggingTestResult, verbosity=2).run(suite)

    logger.info(f"""
=== Test Result ===
 Total:     {result.testsRun}
 Successes: {result.testsRun - len(result.skipped) - len(result.failures) - len(result.errors)}
 Failures:  {len(result.failures)}
 Errors:    {len(result.errors)}
 Skipped:   {len(result.skipped)}
===================
""")

    if conf.DEBUG_MODE == 2:
        print("\nSee Qgis2threejs/qgis2threejs.log for details.")


if __name__ == "__main__":
    import argparse
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtNetwork import QNetworkDiskCache
    from qgis.core import QgsApplication, QgsNetworkAccessManager
    from qgis.testing import start_app

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", type=int, choices=[0, 1, 2], default=2,
                        help="Debug mode (0: OFF, 1 or 2: ON)")
    args = parser.parse_args()

    # start QGIS application
    QgsApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    QGISAPP = start_app()

    # make sure that application startup log has been written
    sys.stdout.flush()

    # set up network disk cache
    manager = QgsNetworkAccessManager.instance()
    cache = QNetworkDiskCache(manager)
    cache.setCacheDirectory(os.path.join(plugin_dir, "tests", "cache"))
    cache.setMaximumCacheSize(50 * 1024 * 1024)
    manager.setCache(cache)

    # run test!
    runTest(args.debug)
