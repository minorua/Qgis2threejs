# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-06

import sys
import os
from qgis.testing import unittest

# Python path setting
plugin_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
plugins_dir = os.path.dirname(plugin_dir)
sys.path.append(plugins_dir)


from Qgis2threejs import conf
conf.TESTING = True


def runTest(debug_mode=None):
    if debug_mode is not None:
        conf.DEBUG_MODE = debug_mode

    from Qgis2threejs.utils import logger

    logger.info(f"Plugin Dir.: {plugin_dir}")
    logger.info(f"DEBUG_MODE: {conf.DEBUG_MODE}")

    # initialize output directory
    from Qgis2threejs.tests.utilities import initOutputDir
    initOutputDir()

    suite = unittest.TestLoader().discover("Qgis2threejs.tests.nongui")
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    import argparse
    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtNetwork import QNetworkDiskCache
    from qgis.core import QgsApplication, QgsNetworkAccessManager
    from qgis.testing import start_app

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", type=int, choices=[0, 1, 2],
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
