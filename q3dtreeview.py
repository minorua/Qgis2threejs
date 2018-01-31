# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DTreeView

                              -------------------
        begin                : 2017-05-30
        copyright            : (C) 2017 Minoru Akagi
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
import os

from PyQt5.Qt import Qt
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QHeaderView, QPushButton, QTreeView
from qgis.core import QgsApplication

from . import q3dconst
from Qgis2threejs.qgis2threejstools import logMessage, pluginDir


class Q3DTreeView(QTreeView):
  """tree view and layer management"""

  def __init__(self, parent=None):
    QTreeView.__init__(self, parent)

    self.layers = []
    self._index = -1

    self.icons = {
      q3dconst.TYPE_DEM: QgsApplication.getThemeIcon("/mIconRaster.svg"),
      q3dconst.TYPE_POINT: QgsApplication.getThemeIcon("/mIconPointLayer.svg"),
      q3dconst.TYPE_LINESTRING: QgsApplication.getThemeIcon("/mIconLineLayer.svg"),
      q3dconst.TYPE_POLYGON: QgsApplication.getThemeIcon("/mIconPolygonLayer.svg")
      }

  def setup(self, iface):
    self.iface = iface

    LAYER_GROUP_ITEMS = ((q3dconst.TYPE_DEM, "DEM"),
                         (q3dconst.TYPE_POINT, "Point"),
                         (q3dconst.TYPE_LINESTRING, "Line"),
                         (q3dconst.TYPE_POLYGON, "Polygon"))

    model = QStandardItemModel(0, 1)
    self.layerParentItem = {}
    for geomType, name in LAYER_GROUP_ITEMS:
      item = QStandardItem(name)
      item.setIcon(self.icons[geomType])
      #item.setData(itemId)
      item.setEditable(False)

      self.layerParentItem[geomType] = item
      model.invisibleRootItem().appendRow([item])

    self.setModel(model)
    self.expandAll()

    self.model().itemChanged.connect(self.treeItemChanged)
    self.doubleClicked.connect(self.treeItemDoubleClicked)

  def addLayer(self, layer):
    # add a layer item to tree view
    item = QStandardItem(layer.name)
    item.setCheckable(True)
    item.setCheckState(Qt.Checked if layer.visible else Qt.Unchecked)
    item.setData(layer.layerId)
    item.setIcon(self.icons[layer.geomType])    #TODO: icon for each object type
    item.setEditable(False)

    self.layerParentItem[layer.geomType].appendRow([item])

  def removeLayer(self, layerId):
    pass

  def getItemByLayerId(self, layerId):
    for parent in self.layerParentItem.values():
      for row in range(parent.rowCount()):
        item = parent.child(row)
        if item.data() == layerId:
          return item
    return None

  def setLayerList(self, layers):
    for layer in layers:
      self.addLayer(layer)

  def treeItemChanged(self, item):
    layer = self.iface.controller.settings.getItemByLayerId(item.data())
    if layer is None:
      return

    visible = bool(item.checkState() == Qt.Checked)

    if layer.geomType == q3dconst.TYPE_IMAGE:    #TODO: image
      return

    layer.visible = visible
    if visible:
      if layer.properties is None:
        layer.properties = self.iface.getDefaultProperties(layer)

      self.iface.exportLayer(layer)
    else:
      obj = {
        "type": "layer",
        "id": layer.jsLayerId,
        "properties": {
          "visible": False
          }
        }
      self.iface.loadJSONObject(obj)

  def treeItemDoubleClicked(self, modelIndex):
    # open layer properties dialog
    layer = self.iface.controller.settings.getItemByLayerId(modelIndex.data(Qt.UserRole + 1))
    if layer is None:
      return
    self.iface.showLayerPropertiesDialog(layer)
