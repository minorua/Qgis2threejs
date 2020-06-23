# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2015-09-06

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
import sys
import os
from qgis.testing import unittest

plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def runTest(debug_mode=None):
    # python path setting
    plugins_dir = os.path.dirname(plugin_dir)
    sys.path.append(plugins_dir)

    from Qgis2threejs import conf
    if debug_mode is not None:
        conf.DEBUG_MODE = debug_mode

    print("DEBUG_MODE is {}.".format(conf.DEBUG_MODE))

    # initialize output directory
    from Qgis2threejs.tests.utilities import initOutputDir
    initOutputDir()

    plugin_name = os.path.basename(plugin_dir)
    suite = unittest.TestLoader().discover(plugin_name + ".tests")
    unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
    import argparse
    from PyQt5.QtCore import Qt
    from PyQt5.QtNetwork import QNetworkDiskCache
    from qgis.core import QgsApplication, QgsNetworkAccessManager
    from qgis.testing import start_app

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", type=int, choices=[0, 1, 2],
                        help="debug mode (0: OFF, 1 or 2: ON)")
    args = parser.parse_args()

    # start QGIS application
    QgsApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
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
