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
from qgis.core import QgsApplication

from . import q3dconst
from .export import ThreeJSExporter
from .exportsettings import ExportSettings
from .qgis2threejstools import logMessage, pluginDir


class Q3DViewerController:

  def __init__(self, qgis_iface, settings=None):
    self.qgis_iface = qgis_iface

    if settings is None:
      defaultSettings = {}
      settings = ExportSettings()
      settings.loadSettings(defaultSettings)
      settings.setMapCanvas(qgis_iface.mapCanvas())

      err_msg = settings.checkValidity()
      if err_msg:
        logMessage(err_msg or "Invalid settings")

    self.settings = settings
    self.exporter = ThreeJSExporter(settings)

    self.iface = None
    self.previewEnabled = True
    self.aborted = False  # layer export aborted
    self.updating = False
    self.layersNeedUpdate = False

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
    if self.updating:
      self.iface.showMessage("Aborting processing...")
      self.aborted = True

  def setPreviewEnabled(self, enabled):
    if self.iface is None:
      return

    self.previewEnabled = enabled
    self.iface.runString("app.resume();" if enabled else "app.pause();");
    if enabled:
      self.updateExtent()
      self.updateScene()

  def updateScene(self, update_world=True, update_layers=True):
    if not self.iface:
      return

    s = self.iface.controller.settings
    self.updating = True
    self.layersNeedUpdate = self.layersNeedUpdate or update_layers
    self.iface.showMessage(self.message1)
    self.iface.progress(0, "Updating scene")

    # export scene
    self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())
    self.iface.loadJSONObject(self.exporter.exportScene(False))

    if update_world:
      # update background color
      ws = s.worldProperties()
      params = "{0}, 1".format(ws.get("lineEdit_Color", 0)) if ws.get("radioButton_Color") else "0, 0"
      self.iface.runString("app.renderer.setClearColor({0});".format(params))

      # coordinate display (geographic/projected)
      if ws.get("radioButton_WGS84", False):
        with open(pluginDir("js/proj4js/proj4.js"), "r") as f:
          self.iface.runString(f.read(), "proj4.js loaded")
      else:
        self.iface.runString("proj4 = undefined;")

    if update_layers:
      layers = s.getLayerList()
      for idx, layer in enumerate(layers):
        self.iface.progress(idx / len(layers) * 100, "Updating layers")
        if layer.updated or (self.layersNeedUpdate and layer.visible):
          if not self._updateLayer(layer):
            break
      self.layersNeedUpdate = False

    self.updating = self.aborted = False
    self.iface.progress()
    self.iface.clearMessage()

  def updateLayer(self, layer):
    self.updating = True
    self.iface.showMessage(self.message1)
    self.iface.progress(0, "Exporting {0}...".format(layer.name))

    self._updateLayer(layer)

    self.updating = self.aborted = False
    self.iface.progress()
    self.iface.clearMessage()

  def _updateLayer(self, layer):
    if self.iface and self.previewEnabled:
      for exporter in self.exporter.exporters(layer):
        if self.aborted:
          return False
        self.iface.loadJSONObject(exporter.build())
        QgsApplication.processEvents()
          # NOTE: process events only for the calling thread
      layer.updated = False
      return True

  def updateExtent(self):
    self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())

  def canvasUpdated(self, painter):
    # update map settings
    self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())

    if self.iface and self.previewEnabled:
      self.updating = True
      self.iface.showMessage(self.message1)
      self.iface.progress(0, "Updating layers")
      layers = self.iface.controller.settings.getLayerList()
      for idx, layer in enumerate(layers):
        self.iface.progress(idx / len(layers) * 100)
        if layer.visible:
          if not self._updateLayer(layer):
            break
      self.layersNeedUpdate = False
      self.updating = self.aborted = False
      self.iface.progress()
      self.iface.clearMessage()

  def canvasExtentChanged(self):
    self.layersNeedUpdate = True
    self.updateScene(False, False)
