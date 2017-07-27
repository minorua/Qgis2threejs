# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DControllerLive

                              -------------------
        begin                : 2016-02-10
        copyright            : (C) 2016 Minoru Akagi
        email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import json
from PyQt5.QtCore import QEventLoop
from qgis.core import QgsApplication, QgsMapLayer, QgsProject, QgsWkbTypes

from . import q3dconst
from Qgis2threejs.export import ThreeJSExporter
from Qgis2threejs.exportsettings import ExportSettings
from Qgis2threejs.qgis2threejstools import getLayersInProject, logMessage


class Q3DViewerController:

  def __init__(self, qgis_iface, pluginManager, settings=None):
    self.qgis_iface = qgis_iface
    self.pluginManager = pluginManager

    if settings is None:
      defaultSettings = {}
      settings = ExportSettings(pluginManager, True)
      settings.loadSettings(defaultSettings)
      settings.setMapCanvas(qgis_iface.mapCanvas())

      err_msg = settings.checkValidity()
      if err_msg:
        logMessage(err_msg or "Invalid settings")

    self.settings = settings
    self.exporter = ThreeJSExporter(settings)

    self.iface = None
    self.enabled = True
    self.extentUpdated = False

  def connectToIface(self, iface):
    """iface: Q3DViewerInterface"""
    self.iface = iface

    self.qgis_iface.mapCanvas().renderComplete.connect(self.canvasUpdated)
    self.qgis_iface.mapCanvas().extentsChanged.connect(self.canvasExtentChanged)

  def disconnectFromIface(self):
    self.iface = None

    self.qgis_iface.mapCanvas().renderComplete.disconnect(self.canvasUpdated)
    self.qgis_iface.mapCanvas().extentsChanged.disconnect(self.canvasExtentChanged)

  def exportScene(self):
    if self.iface:
      self.iface.loadJSONObject(self.exporter.exportScene(False))

  def exportLayer(self, layer):
    if self.iface and self.enabled:
      if layer.geomType == q3dconst.TYPE_DEM:
        for exporter in self.exporter.demExporters(layer):
          self.iface.loadJSONObject(exporter.build())
          QgsApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
            # NOTE: process events only for the calling thread

      elif layer.geomType in [q3dconst.TYPE_POINT, q3dconst.TYPE_LINESTRING, q3dconst.TYPE_POLYGON]:
        for exporter in self.exporter.vectorExporters(layer):
          self.iface.loadJSONObject(exporter.build())
          QgsApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

      layer.updated = False

  def setEnabled(self, enabled):
    if self.iface is None:
      return

    self.enabled = enabled
    self.iface.runString("app.resume();" if enabled else "app.pause();");
    if enabled:
      # update layers
      for layerId, layer in enumerate(self.iface.controller.settings.getLayerList()):
        if layer.updated or (self.extentUpdated and layer.visible):
          self.exportLayer(layer)

      self.extentUpdated = False

  def updateExtent(self):
    self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())

  def canvasUpdated(self, painter):
    # update map settings
    self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())

    if self.iface and self.enabled:
      for layer in self.iface.controller.settings.getLayerList():
        if layer.visible:
          self.exportLayer(layer)
      self.extentUpdated = False

  def canvasExtentChanged(self):
    self.extentUpdated = True

    # update map settings
    self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())

    # update scene properties
    self.exportScene()
