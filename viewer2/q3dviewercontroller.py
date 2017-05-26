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
from qgis.PyQt.QtCore import Qt, QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.core import QgsMapLayer, QgsProject, QgsWkbTypes

from . import q3dconst
from Qgis2threejs.export import ThreeJSExporter
from Qgis2threejs.exportsettings import ExportSettings
from Qgis2threejs.propertypages import DEMPropertyPage, VectorPropertyPage
from Qgis2threejs.qgis2threejscore import MapTo3D
from Qgis2threejs.qgis2threejsdialog import RectangleMapTool
from Qgis2threejs.qgis2threejstools import getLayersInProject, logMessage
from Qgis2threejs.writer import ThreejsJSWriter, writeSimpleDEM, writeVector    #writeMultiResDEM


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
        #return

    self.settings = settings
    self.exporter = ThreeJSExporter(settings)

  def setViewerInterface(self, iface):
    self.iface = iface
    self.qgis_iface.mapCanvas().renderComplete.connect(iface.canvasUpdated)
    self.qgis_iface.mapCanvas().extentsChanged.connect(iface.canvasExtentChanged)

  def getLayerList(self):
    layers = []
    for plugin in self.pluginManager.demProviderPlugins():
      layers.append({"layerId": "plugin:" + plugin.providerId(), "name": plugin.providerName(), "geomType": q3dconst.TYPE_DEM})

    for layer in getLayersInProject():
      layerType = layer.type()
      if layerType == QgsMapLayer.VectorLayer:
        geomType = {QgsWkbTypes.PointGeometry: q3dconst.TYPE_POINT,
                    QgsWkbTypes.LineGeometry: q3dconst.TYPE_LINESTRING,
                    QgsWkbTypes.PolygonGeometry: q3dconst.TYPE_POLYGON,
                    QgsWkbTypes.UnknownGeometry: None,
                    QgsWkbTypes.NullGeometry: None}[layer.geometryType()]

      elif layerType == QgsMapLayer.RasterLayer and layer.providerType() == "gdal" and layer.bandCount() == 1:
        geomType = q3dconst.TYPE_DEM
      else:
        geomType = q3dconst.TYPE_IMAGE
        continue

      if geomType is not None:
        properties = json.loads(q3dconst.DEFAULT_PROPERTIES[geomType])
        layers.append({"layerId": layer.id(), "name": layer.name(), "geomType": geomType, "properties": properties})

    return layers

  def createScene(self):
    self.iface.loadJSONObject(self.exporter.exportScene(False))

  def createLayer(self, layer):
    self._exportLayer(layer)

  def updateLayer(self, layer):
    self._exportLayer(layer)

  def _exportLayer(self, layer):
    if layer["geomType"] == q3dconst.TYPE_DEM:
      self.iface.loadJSONObject(self.exporter.exportDEMLayer(layer["layerId"], layer["properties"], layer["jsLayerId"], layer["visible"]))
    elif layer["geomType"] in [q3dconst.TYPE_POINT, q3dconst.TYPE_LINESTRING, q3dconst.TYPE_POLYGON]:
      self.iface.loadJSONObject(self.exporter.exportVectorLayer(layer["layerId"], layer["properties"], layer["jsLayerId"], layer["visible"]))

  def updateMapCanvasExtent(self):
    # update extent in export settings
    self.exporter.settings.setMapCanvas(self.qgis_iface.mapCanvas())

    # update scene properties
    self.iface.loadJSONObject(self.exporter.exportScene(False))

  def showPropertiesDialog(self, id, layerId, geomType, properties=None):
    layer = QgsProject.instance().mapLayer(str(layerId))
    if layer is None:
      return

    properties = properties or {}
    dialog = PropertiesDialog(self.qgis_iface, self.objectTypeManager, self.pluginManager)
    dialog.setLayer(id, layer, geomType, properties)
    dialog.show()
    dialog.propertiesChanged.connect(self.propertiesChanged)
    dialog.exec_()

  def propertiesChanged(self, id, properties):
    pass
    #self.iface.notify({"code": q3dconst.N_LAYER_PROPERTIES_CHANGED, "id": id, "properties": properties})
