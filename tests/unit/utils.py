# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys

# configuration for testing
from ... import conf
conf.TESTING = True

from ...utils import pluginDir
from ...utils.logging import getLogger

# set up logger handlers for tests
logger = getLogger(conf.PLUGIN_NAME,
                   stream=True,
                   filepath=pluginDir("qgis2threejs.log") if conf.DEBUG_MODE == 2 else "",
                   list_handler=True)

web_logger = getLogger(name=conf.PLUGIN_NAME + "Web",
                       stream=True,
                       filepath=pluginDir("qgis2threejs_web.log") if conf.DEBUG_MODE == 2 else "",
                       list_handler=True)

logger.info(f"TESTING: {conf.TESTING}")
logger.info(f"DEBUG_MODE: {conf.DEBUG_MODE}")

# python path setting
plugin_dir = pluginDir()
plugins_dir = os.path.dirname(plugin_dir)
if plugins_dir not in sys.path:
    sys.path.append(plugins_dir)


app = None


def start_app():
    global app

    if app:
        return app

    logger.info("Starting QGIS application...")

    from qgis.PyQt.QtCore import Qt
    from qgis.PyQt.QtNetwork import QNetworkDiskCache
    from qgis.core import QgsApplication, QgsNetworkAccessManager
    from qgis.testing import start_app as _start_app

    # start QGIS application
    QgsApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = _start_app()

    # make sure that application startup log has been written
    sys.stdout.flush()

    # set up network disk cache
    manager = QgsNetworkAccessManager.instance()
    cache = QNetworkDiskCache(manager)
    cache.setCacheDirectory(pluginDir("tests", "cache"))
    cache.setMaximumCacheSize(50 * 1024 * 1024)
    manager.setCache(cache)

    return app

def stop_app():
    return      # stop_app might cause crash in some environments

    logger.info("Stopping QGIS application...")

    from qgis.testing import stop_app as _stop_app
    _stop_app()
