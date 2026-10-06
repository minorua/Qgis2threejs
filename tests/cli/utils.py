# -*- coding: utf-8 -*-
# (C) 2025 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys

from qgis.PyQt.QtCore import QSize
from qgis.core import QgsMapSettings, QgsProject

from ... import conf
from ...utils.basic import pluginDir
from ...utils import logging

# constants
TEX_WIDTH, TEX_HEIGHT = (1024, 1024)

# run_test.py results are written to log files by default, so suppress console output
log_to_stream = not sys.argv[0].endswith("run_test.py")

# configure logger handlers for tests
logging.configureLoggers(is_test=True, log_to_stream=log_to_stream)

logger = logging.logger
logger.info(f"TESTING: {conf.IS_TESTING}")
logger.info(f"DEBUG_MODE: {conf.DEBUG_MODE}")
logger.info(f"sys.argv: {sys.argv}")

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


def loadProject(filename):
    project = QgsProject.instance()
    project.clear()

    if not project.read(filename):
        raise RuntimeError(f"Failed to load the project: {project.error()} {filename}")

    map_settings = QgsMapSettings()
    map_settings.setDestinationCrs(project.crs())
    map_settings.setTransformContext(project.transformContext())
    map_settings.setLayers(project.layerTreeRoot().checkedLayers())
    map_settings.setExtent(project.viewSettings().defaultViewExtent())
    map_settings.setOutputSize(QSize(TEX_WIDTH, TEX_HEIGHT))
    map_settings.setBackgroundColor(project.backgroundColor())

    return map_settings
