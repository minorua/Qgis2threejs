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
      q3dconst.TYPE_POLYGON: QgsApplication.getThemeIcon("/mIconPolygonLayer.svg"),
      "settings": QIcon(os.path.join(pluginDir(), "icons", "settings.png"))
      }

  def setup(self, iface):
    self.iface = iface

    TREE_TOP_ITEMS = ("Scene", "Lights & Shadow", "Layers")    # tr
    LAYER_GROUP_ITEMS = ((q3dconst.TYPE_DEM, "DEM"),
                         (q3dconst.TYPE_POINT, "Point"),
                         (q3dconst.TYPE_LINESTRING, "Line"),
                         (q3dconst.TYPE_POLYGON, "Polygon"))

    model = QStandardItemModel(0, 2)
    self.treeItems = []
    for name in TREE_TOP_ITEMS:
      item = QStandardItem(name)
      item.setIcon(QgsApplication.getThemeIcon("/propertyicons/CRS.svg"))
      #item.setData(itemId)
      item.setEditable(False)
      self.treeItems.append(item)
      model.invisibleRootItem().appendRow([item])

    itemLayers = self.treeItems[2]   # Layers
    self.layerParentItem = {}
    for geomType, name in LAYER_GROUP_ITEMS:
      item = QStandardItem(name)
      item.setIcon(self.icons[geomType])
      #item.setData(itemId)
      item.setEditable(False)
      itemLayers.appendRow([item])
      self.layerParentItem[geomType] = item

    self.setModel(model)
    self.header().setStretchLastSection(False)
    self.header().setSectionResizeMode(0, QHeaderView.Stretch)
    self.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
    self.expandAll()

    self.model().itemChanged.connect(self.treeItemChanged)
    self.doubleClicked.connect(self.treeItemDoubleClicked)

  def addLayer(self, layerId, name, geomType, visible=True, properties=None):
    itemId = len(self.layers)

    self.layers.append({
      "id": itemId,
      "layerId": layerId,
      "name": name,
      "geomType": geomType,
      "visible": visible,
      "properties": properties,
      "jsLayerId": "{}_{}".format(itemId, layerId[:8])
    })

    # add a layer item to tree view
    item = QStandardItem(name)
    item.setCheckable(True)
    item.setCheckState(Qt.Checked if visible else Qt.Unchecked)
    item.setData(itemId)
    item.setIcon(self.icons[geomType])    #TODO: icon for each object type
    item.setEditable(False)

    item2 = QStandardItem()
    self.layerParentItem[geomType].appendRow([item, item2])

    # add a button
    button = QPushButton()
    button.setIcon(self.icons["settings"])
    button.setStyleSheet("background-color: rgba(255, 255, 255, 0);")
    button.setMaximumHeight(16)
    button.setMaximumWidth(20)
    self.setIndexWidget(item2.index(), button)

  def removeLayer(self, id):
    for index, layer in enumerate(self.layers):
      if layer["id"] == id:
        self.layers[index] = None
        return True
    return False

  def treeItemChanged(self, item):
    itemId = item.data()
    layer = self.layers[itemId]
    visible = bool(item.checkState() == Qt.Checked)

    if layer["geomType"] == q3dconst.TYPE_IMAGE:    #TODO: image
      return

    layer["visible"] = visible
    if visible:
      if layer["properties"] is None:
        layer["properties"] = self.iface.getDefaultProperties(layer)

      self.iface.exportLayer(layer)
    else:
      obj = {
        "type": "layer",
        "id": layer["jsLayerId"],
        "properties": {
          "visible": False
          }
        }
      self.iface.loadJSONObject(obj)

  def treeItemDoubleClicked(self, modelIndex):
    # open layer properties dialog
    index = modelIndex.data(Qt.UserRole + 1)
    if index is None:
      return
    layer = self.layers[index]     #TODO: index or layerId
    self.iface.showLayerPropertiesDialog(layer)

    #self.iface.notify({"code": q3dconst.N_LAYER_DOUBLECLICKED, "layer": self.layerManager.layers[idx]})
