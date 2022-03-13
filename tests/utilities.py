# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-14

import os
import shutil

from PyQt5.QtCore import qDebug
from PyQt5.QtGui import QColor
from PyQt5.QtXml import QDomDocument
from qgis.core import QgsMapSettings, QgsProject

from Qgis2threejs.qgis2threejstools import getLayersByLayerIds


def pluginPath(subdir=None):
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    plugin_dir = os.path.dirname(tests_dir)
    if subdir is None:
        return plugin_dir
    return os.path.join(plugin_dir, subdir)


def dataPath(subdir=None):
    data_path = os.path.join(os.path.dirname(__file__), "data")
    if subdir is None:
        return data_path
    return os.path.join(data_path, subdir)


def expectedDataPath(subdir=None):
    data_path = os.path.join(os.path.dirname(__file__), "expected")
    if not os.path.isdir(data_path):
        os.mkdir(data_path)
    if subdir is None:
        return data_path
    return os.path.join(data_path, subdir)


def outputPath(subdir=None):
    data_path = os.path.join(os.path.dirname(__file__), "output")
    if subdir is None:
        return data_path
    return os.path.join(data_path, subdir)


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
        qDebug(msg.encode("utf-8"))
    else:
        qDebug(str(msg))
