# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2015-09-14

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
import codecs
import os
import shutil
import sys

from PyQt4.QtCore import QFileInfo, qDebug
from PyQt4.QtGui import QColor
from PyQt4.QtXml import QDomDocument
from qgis.core import QgsCoordinateReferenceSystem, QgsMapLayerRegistry, QgsMapSettings, QgsPoint, QgsProject, QgsRectangle
from qgis.gui import QgsMapCanvas, QgsLayerTreeMapCanvasBridge


def pluginPath(subdir=None):
  tests_dir = os.path.dirname(os.path.abspath(__file__).decode(sys.getfilesystemencoding()))
  plugin_dir = os.path.dirname(tests_dir)
  if subdir is None:
    return plugin_dir
  return os.path.join(plugin_dir, subdir)


def dataPath(subdir=None):
  data_path = pluginPath(os.path.join("tests", "data"))
  if subdir is None:
    return data_path
  return os.path.join(data_path, subdir)


def outputPath(subdir=None):
  data_path = pluginPath(os.path.join("tests", "output"))
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
  assert os.path.exists(filename), "project file does not exist: " + filename

  QgsProject.instance().read(QFileInfo(filename))
  assert QgsMapLayerRegistry.instance().mapLayers(), "no layers in map layer registry"

  with codecs.open(filename, "r", "utf-8") as f:
    doc = QDomDocument()
    doc.setContent(f.read())

  # map settings
  mapSettings = QgsMapSettings()
  mapSettings.readXML(doc.elementsByTagName("mapcanvas").at(0))

  # visible layers
  layerIds = []
  nodes = doc.elementsByTagName("legendlayer")
  for i in range(nodes.count()):
    elem = nodes.at(i).toElement().elementsByTagName("legendlayerfile").at(0).toElement()
    if elem.attribute("visible") == "1":
      layerIds.append(elem.attribute("layerid"))
  mapSettings.setLayers(layerIds)

  # canvas color
  red = int(doc.elementsByTagName("CanvasColorRedPart").at(0).toElement().text())
  green = int(doc.elementsByTagName("CanvasColorGreenPart").at(0).toElement().text())
  blue = int(doc.elementsByTagName("CanvasColorBluePart").at(0).toElement().text())
  mapSettings.setBackgroundColor(QColor(red, green, blue))

  return mapSettings


def log(msg):
  if isinstance(msg, unicode):
    qDebug(msg.encode("utf-8"))
  else:
    qDebug(str(msg))
