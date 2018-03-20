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
from PyQt5.QtCore import QEventLoop
from qgis.core import QgsApplication

from . import q3dconst
from .export import ThreeJSExporter
from .exportsettings import ExportSettings
from .qgis2threejstools import logMessage


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
    self.enabled = True   # preview enabled
    self.aborted = False  # layer export aborted
    self.exporting = False
    self.extentUpdated = False

    self.message1 = "Press ESC key to abort processing"

  def connectToIface(self, iface):
    """iface: Q3DViewerInterface"""
    self.iface = iface

    self.qgis_iface.mapCanvas().renderComplete.connect(self.canvasUpdated)
    self.qgis_iface.mapCanvas().extentsChanged.connect(self.canvasExtentChanged)

  def disconnectFromIface(self):
    self.iface = None

    self.qgis_iface.mapCanvas().renderComplete.disconnect(self.canvasUpdated)
    self.qgis_iface.mapCanvas().extentsChanged.disconnect(self.canvasExtentChanged)

  def abort(self):
    if self.exporting:
      self.iface.showMessage("Aborting processing...")
      self.aborted = True

  def exportScene(self):
    if self.iface:
      self.extentUpdated = True
      self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())
      self.iface.loadJSONObject(self.exporter.exportScene(False))

  def exportLayer(self, layer):
    self.exporting = True
    self.iface.showMessage(self.message1)
    self.iface.progress(0, "Exporting {0}...".format(layer.name))

    self._exportLayer(layer)

    self.exporting = self.aborted = False
    self.iface.progress()
    self.iface.clearMessage()

  def _exportLayer(self, layer):
    if self.iface and self.enabled:
      if layer.geomType == q3dconst.TYPE_DEM:
        for exporter in self.exporter.demExporters(layer):
          if self.aborted:
            return False
          self.iface.loadJSONObject(exporter.build())
          QgsApplication.processEvents()
            # NOTE: process events only for the calling thread

      elif layer.geomType in [q3dconst.TYPE_POINT, q3dconst.TYPE_LINESTRING, q3dconst.TYPE_POLYGON]:
        for exporter in self.exporter.vectorExporters(layer):
          if self.aborted:
            return False
          self.iface.loadJSONObject(exporter.build())
          QgsApplication.processEvents()

      layer.updated = False
      return True

  def setEnabled(self, enabled):
    if self.iface is None:
      return

    self.enabled = enabled
    self.iface.runString("app.resume();" if enabled else "app.pause();");
    if enabled:
      # update layers
      self.exporting = True
      self.iface.showMessage(self.message1)
      self.iface.progress(0, "Updating layers")
      layers = self.iface.controller.settings.getLayerList()
      for idx, layer in enumerate(layers):
        self.iface.progress(idx / len(layers) * 100)
        if layer.updated or (self.extentUpdated and layer.visible):
          if not self._exportLayer(layer):
            break

      self.extentUpdated = False
      self.exporting = self.aborted = False
      self.iface.progress()
      self.iface.clearMessage()
      
  def updateExtent(self):
    self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())

  def canvasUpdated(self, painter):
    # update map settings
    self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())

    if self.iface and self.enabled:
      self.exporting = True
      self.iface.showMessage(self.message1)
      self.iface.progress(0, "Updating layers")
      layers = self.iface.controller.settings.getLayerList()
      for idx, layer in enumerate(layers):
        self.iface.progress(idx / len(layers) * 100)
        if layer.visible:
          if not self._exportLayer(layer):
            break
      self.extentUpdated = False
      self.exporting = self.aborted = False
      self.iface.progress()
      self.iface.clearMessage()

  def canvasExtentChanged(self):
    self.exportScene()
