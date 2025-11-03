# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-06

import traceback
from qgis.testing import unittest

from Qgis2threejs import conf
from Qgis2threejs.utils import pluginDir
from Qgis2threejs.utils.logging import getLogger
from Qgis2threejs.tests.utils import initOutputDir, outputPath


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

    from Qgis2threejs.tests.nongui import utils     # need to import the utils module before setting up logger handlers

    # set up logger handlers for tests
    logger = getLogger(conf.PLUGIN_NAME,
                       stream=False,
                       filepath=pluginDir("qgis2threejs.log") if conf.DEBUG_MODE == 2 else "",
                       list_handler=True)
    logger.info("Starting tests...")
    logger.info(f"TESTING: {conf.TESTING}")
    logger.info(f"DEBUG_MODE: {conf.DEBUG_MODE}")
    logger.info(f"Plugin Dir: {pluginDir()}")
    logger.info(f"Output Dir: {outputPath()}")

    # initialize output directory
    initOutputDir()

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

    print("\nSee Qgis2threejs/qgis2threejs.log for details.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", type=int, choices=[0, 1, 2], default=2,
                        help="Debug mode (0: OFF, 1 or 2: ON)")
    args = parser.parse_args()

    # run test!
    runTest(args.debug)
