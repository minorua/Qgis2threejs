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
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QAction, QMenu, QMessageBox, QTreeView
from qgis.core import QgsApplication

from . import q3dconst
from .qgis2threejstools import pluginDir


class Q3DTreeView(QTreeView):
    """layer tree view"""

    def __init__(self, parent=None):
        QTreeView.__init__(self, parent)

        self.layers = []
        self._index = -1

        self.icons = {
            q3dconst.TYPE_DEM: QgsApplication.getThemeIcon("/mIconRaster.svg"),
            q3dconst.TYPE_POINT: QgsApplication.getThemeIcon("/mIconPointLayer.svg"),
            q3dconst.TYPE_LINESTRING: QgsApplication.getThemeIcon("/mIconLineLayer.svg"),
            q3dconst.TYPE_POLYGON: QgsApplication.getThemeIcon("/mIconPolygonLayer.svg"),
            q3dconst.TYPE_POINTCLOUD: QIcon(pluginDir("images", "pointcloud.svg"))
        }

        self.actionProperties = QAction("Properties", self)
        self.actionProperties.triggered.connect(self.showPropertiesDialog)

        self.actionAddPCLayer = QAction("Add Point Cloud layer...", self)
        self.actionAddPCLayer.triggered.connect(self.showAddPointCloudLayerDialog)

        self.actionRemovePCLayer = QAction("Remove from layer tree", self)
        self.actionRemovePCLayer.triggered.connect(self.removePointCloudLayer)

        # context menu for map layer
        self.contextMenu = QMenu(self)
        self.contextMenu.addAction(self.actionProperties)

        # context menu for point cloud group
        self.contextMenuPCG = QMenu(self)
        self.contextMenuPCG.addAction(self.actionAddPCLayer)

        # context menu for point cloud layer
        self.contextMenuPC = QMenu(self)
        self.contextMenuPC.addAction(self.actionRemovePCLayer)
        self.contextMenuPC.addSeparator()
        self.contextMenuPC.addAction(self.actionProperties)

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.customContextMenuRequested.connect(self.showContextMenu)
        self.doubleClicked.connect(self.showPropertiesDialog)

    def setup(self, iface):
        self.iface = iface

        LAYER_GROUP_ITEMS = ((q3dconst.TYPE_DEM, "DEM"),
                             (q3dconst.TYPE_POINT, "Point"),
                             (q3dconst.TYPE_LINESTRING, "Line"),
                             (q3dconst.TYPE_POLYGON, "Polygon"),
                             (q3dconst.TYPE_POINTCLOUD, "Point Cloud"))

        model = QStandardItemModel(0, 1)
        self.layerParentItem = {}
        for geomType, name in LAYER_GROUP_ITEMS:
            item = QStandardItem(name)
            item.setIcon(self.icons[geomType])
            item.setEditable(False)

            self.layerParentItem[geomType] = item
            model.invisibleRootItem().appendRow([item])

        self.setModel(model)
        self.expandAll()

        self.model().itemChanged.connect(self.treeItemChanged)

    def addLayer(self, layer):
        # add a layer item to tree view
        item = QStandardItem(layer.name)
        item.setCheckable(True)
        item.setCheckState(Qt.Checked if layer.visible else Qt.Unchecked)
        item.setData(layer.layerId)
        item.setIcon(self.icons[layer.geomType])
        item.setEditable(False)

        self.layerParentItem[layer.geomType].appendRow([item])

    def removeLayer(self, layerId):
        item = self.getItemByLayerId(layerId)
        if item:
            item.parent().removeRow(item.row())

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

    def updateLayersCheckState(self, settings):
        self.blockSignals(True)
        for parent in self.layerParentItem.values():
            for row in range(parent.rowCount()):
                item = parent.child(row)
                layer = settings.getItemByLayerId(item.data())
                item.setCheckState(Qt.Checked if layer and layer.visible else Qt.Unchecked)

        self.blockSignals(False)

    def uncheckAll(self):
        for parent in self.layerParentItem.values():
            for idx in range(parent.rowCount()):
                parent.child(idx).setCheckState(Qt.Unchecked)

    def treeItemChanged(self, item):
        layer = self.iface.settings.getItemByLayerId(item.data())
        if layer is None:
            return

        layer.visible = (item.checkState() == Qt.Checked)
        if layer.visible and not layer.properties:
            layer.properties = self.iface.wnd.getDefaultProperties(layer)

        self.iface.requestLayerUpdate(layer)

    def showContextMenu(self, pos):
        i = self.indexAt(pos)
        data = self.model().data(i, Qt.UserRole + 1)
        if data is not None:
            if data.startswith("pc:"):
                self.contextMenuPC.exec_(self.mapToGlobal(pos))
            else:
                self.contextMenu.exec_(self.mapToGlobal(pos))
        elif self.model().itemFromIndex(i) == self.layerParentItem[q3dconst.TYPE_POINTCLOUD]:
            self.contextMenuPCG.exec_(self.mapToGlobal(pos))

    def showPropertiesDialog(self, _=None):
        # open layer properties dialog
        data = self.model().data(self.currentIndex(), Qt.UserRole + 1)
        layer = self.iface.settings.getItemByLayerId(data)
        if layer is not None:
            self.iface.wnd.showLayerPropertiesDialog(layer)

    def showAddPointCloudLayerDialog(self, _=None):
        self.iface.wnd.showAddPointCloudLayerDialog()

    def removePointCloudLayer(self, _=None):
        data = self.model().data(self.currentIndex(), Qt.UserRole + 1)

        layer = self.iface.settings.getItemByLayerId(data)
        if layer is None:
            return

        if QMessageBox.question(self, "Qgis2threejs", "Are you sure you want to remove the layer '{0}' from layer tree?".format(layer.name)) != QMessageBox.Yes:
            return

        self.iface.removeLayerRequest.emit(layer.layerId)
        self.removeLayer(layer.layerId)

    def clearPointCloudLayers(self):
        parent = self.layerParentItem[q3dconst.TYPE_POINTCLOUD]
        if parent.hasChildren():
            parent.removeRows(0, parent.rowCount())
