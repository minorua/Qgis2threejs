# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-14

import os
import shutil

from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtXml import QDomDocument
from qgis.core import QgsMapSettings, QgsProject

from Qgis2threejs.utils import getLayersByLayerIds, logger, pluginDir

MY_TEST_TEMPDIR = "E:/dev/qgis2threejs_test"


def testDir(*subdirs):
    return pluginDir("tests", *subdirs)


def dataPath(*subdirs):
    dataDir = testDir("data")
    if subdirs:
        return os.path.join(dataDir, *subdirs)
    return dataDir


def expectedDataPath(*subdirs):
    if os.path.exists(MY_TEST_TEMPDIR):
        dataDir = MY_TEST_TEMPDIR + "/expected"
    else:
        dataDir = testDir("expected")
        logger.warning("Expected data not exist.")      # TODO

    if subdirs:
        return os.path.join(dataDir, *subdirs)
    return dataDir


def outputPath(*subdirs):
    if os.path.exists(MY_TEST_TEMPDIR):
        dataDir = MY_TEST_TEMPDIR + "/output"
    else:
        dataDir = testDir("output")

    if subdirs:
        return os.path.join(dataDir, *subdirs)
    return dataDir


def initOutputDir():
    """initialize output directory"""
    out_dir = outputPath()
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.mkdir(out_dir)


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

    return mapSettings


def log(msg):
    if isinstance(msg, str):
        logger.info(msg.encode("utf-8"))
    else:
        logger.info(str(msg))
