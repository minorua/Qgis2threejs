# -*- coding: utf-8 -*-
# (C) 2025 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from ... import conf
conf.TESTING = True

import os
import sys

from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtXml import QDomDocument
from qgis.core import QgsMapSettings, QgsProject

from ...core.mapextent import MapExtent
from ...utils import getLayersByLayerIds, pluginDir
from ...utils.logging import configureLoggers, logger

# constants
TEX_WIDTH, TEX_HEIGHT = (1024, 1024)

# run_test.py results are written to log files by default, so suppress console output
log_to_stream = not sys.argv[0].endswith("run_test.py")

# configure logger handlers for tests
configureLoggers(is_test=True, log_to_stream=log_to_stream)

logger.info(f"TESTING: {conf.TESTING}")
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
    # clear the map layer registry
    QgsProject.instance().removeAllMapLayers()

    assert os.path.exists(filename), "project file does not exist: " + filename

    # load the project
    QgsProject.instance().read(filename)
    assert QgsProject.instance().mapLayers(), "no layers in map layer registry"

    doc = QDomDocument()
    with open(filename, encoding="utf-8") as f:
        doc.setContent(f.read())

    # map settings
    mapSettings = QgsMapSettings()
    mapSettings.readXml(doc.elementsByTagName("mapcanvas").at(0))

    # visible layers
    layerIds = []
    nodes = doc.elementsByTagName("legendlayer")
    for i in range(nodes.count()):
        elem = nodes.at(i).toElement().elementsByTagName("legendlayerfile").at(0).toElement()
        if elem.attribute("visible") == "1":
            layerIds.append(elem.attribute("layerid"))
    mapSettings.setLayers(getLayersByLayerIds(layerIds))

    # canvas color
    red = int(doc.elementsByTagName("CanvasColorRedPart").at(0).toElement().text())
    green = int(doc.elementsByTagName("CanvasColorGreenPart").at(0).toElement().text())
    blue = int(doc.elementsByTagName("CanvasColorBluePart").at(0).toElement().text())
    mapSettings.setBackgroundColor(QColor(red, green, blue))

    # extent
    MapExtent(mapSettings.extent().center(),
              mapSettings.extent().height(),
              mapSettings.extent().height(), 0).toMapSettings(mapSettings)

    # texture base size
    mapSettings.setOutputSize(QSize(TEX_WIDTH, TEX_HEIGHT))

    return mapSettings
