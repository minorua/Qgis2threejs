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
from PyQt5.QtGui import QColor, QIcon, QPixmap, QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QAction, QMenu, QMessageBox, QTreeView
from qgis.core import QgsApplication

from .q3dconst import LayerType, DEMMtlType


class Q3DTreeView(QTreeView):
    """layer tree view"""

    LAYER_GROUP_ITEMS = ((LayerType.DEM, "DEM"),
                         (LayerType.POINT, "Point"),
                         (LayerType.LINESTRING, "Line"),
                         (LayerType.POLYGON, "Polygon"),
                         (LayerType.POINTCLOUD, "Point Cloud"))

    def __init__(self, parent=None):
        QTreeView.__init__(self, parent)

        self.layers = []
        self._index = -1

        self.actionProperties = QAction("Properties...", self)
        self.actionProperties.triggered.connect(self.onDoubleClicked)

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

        self.setExpandsOnDoubleClick(False)
        self.doubleClicked.connect(self.onDoubleClicked)

    def setup(self, iface, icons):
        self.iface = iface      # Q3DViewerInterface
        self.icons = icons

        model = QStandardItemModel(0, 1)
        self.layerGroupItems = {}
        for typ, name in self.LAYER_GROUP_ITEMS:
            item = QStandardItem(name)
            item.setIcon(self.icons[typ])
            item.setEditable(False)

            self.layerGroupItems[typ] = item
            model.invisibleRootItem().appendRow([item])

        self.setModel(model)
        self.expandAll()

        self.model().itemChanged.connect(self.treeItemChanged)

    def addLayer(self, layer):
        # add a layer item to tree view
        item = QStandardItem(layer.name)
        item.setCheckable(True)
        item.setData(layer.layerId)
        # item.setIcon(self.icons[layer.type])
        item.setEditable(False)

        if layer.visible:
            item.setCheckState(Qt.Checked)

            font = item.font()
            font.setBold(True)
            item.setFont(font)

        self.layerGroupItems[layer.type].appendRow([item])

        self.updateLayerMaterials(item)

    def addLayers(self, layers):
        for layer in layers:
            self.addLayer(layer)

    def removeLayer(self, layerId):
        item = self.itemFromLayerId(layerId)
        if item:
            item.parent().removeRow(item.row())

    def layerFromIndex(self, index):
        layerId = self.model().data(index, Qt.UserRole + 1)
        return self.iface.settings.getLayer(layerId)

    def itemFromLayerId(self, layerId):
        for parent in self.layerGroupItems.values():
            for row in range(parent.rowCount()):
                item = parent.child(row)
                if item.data() == layerId:
                    return item
        return None

    def iconForMtl(self, mtl):
        mtype = mtl.get("type")
        if mtype == DEMMtlType.LAYER:
            return QgsApplication.getThemeIcon("algorithms/mAlgorithmMergeLayers.svg")

        elif mtype == DEMMtlType.MAPCANVAS:
            return QgsApplication.getThemeIcon("mLayoutItemMap.svg")

        elif mtype == DEMMtlType.FILE:
            return QgsApplication.getThemeIcon("mIconFile.svg")

        elif mtype == DEMMtlType.COLOR:
            color = mtl.get("properties", {}).get("colorButton_Color").replace("0x", "#")
            if color:
                pixmap = QPixmap(32, 32)
                pixmap.fill(QColor(color))
                return QIcon(pixmap)

        return QIcon()

    def updateLayerMaterials(self, layerItem, layer=None):
        layerItem.removeRows(0, layerItem.rowCount())

        layer = layer or self.iface.settings.getLayer(layerItem.data())
        if layer is None or not layer.visible:
            return

        # add material items if layer has multiple materials
        mtls = layer.properties.get("materials", [])
        if len(mtls) < 2:
            return

        currentId = layer.properties.get("mtlId")

        for mtl in mtls:
            id = mtl.get("id")
            item = QStandardItem(mtl.get("name", ""))
            item.setData(id)
            item.setIcon(self.iconForMtl(mtl))
            item.setEditable(False)
            # item.setCheckable(True)
            # item.setCheckState(Qt.Unchecked)        # Qt.Checked if layer.visible else Qt.Unchecked)

            if id == currentId:
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            layerItem.appendRow([item])

        self.expand(layerItem.index())

    def updateLayersCheckState(self, settings):
        self.blockSignals(True)
        for parent in self.layerGroupItems.values():
            for row in range(parent.rowCount()):
                item = parent.child(row)
                layer = settings.getLayer(item.data())
                item.setCheckState(Qt.Checked if layer and layer.visible else Qt.Unchecked)

        self.blockSignals(False)

    def uncheckAll(self):
        for parent in self.layerGroupItems.values():
            for idx in range(parent.rowCount()):
                parent.child(idx).setCheckState(Qt.Unchecked)

    def currentChanged(self, current, previous):
        QTreeView.currentChanged(self, current, previous)

        idx = current
        depth = 0
        while idx.parent().isValid():
            depth += 1
            idx = idx.parent()

        if depth == 2:
            # DEM material
            layer = self.layerFromIndex(current.parent())
            if layer:
                mtlId = self.model().data(current, Qt.UserRole + 1)  # set with item.setData()
                layer.properties["mtlId"] = mtlId

                layer = layer.clone()
                layer.opt.onlyMaterial = True
                self.iface.updateLayerRequest.emit(layer)

            item = self.model().itemFromIndex(current)
            parent = item.parent()
            font = item.font()
            for row in range(parent.rowCount()):
                font.setBold(row == item.row())
                parent.child(row).setFont(font)

    # checkbox toggled
    def treeItemChanged(self, item):
        layer = self.iface.settings.getLayer(item.data())
        if layer is None:
            return

        checked = (item.checkState() == Qt.Checked)
        layer.visible = checked
        if layer.visible and not layer.properties:
            layer.properties = self.iface.wnd.getDefaultProperties(layer)

        self.iface.requestLayerUpdate(layer)

        font = item.font()
        font.setBold(checked)
        item.setFont(font)

        self.updateLayerMaterials(item, layer)

        self.iface.wnd.ui.animationPanel.tree.setLayerHidden(layer.layerId, not checked)

    def indexDepth(self, idx):
        depth = 0
        while idx.parent().isValid():
            depth += 1
            idx = idx.parent()
        return depth    #TODO: self.model().data(idx, Qt.UserRole)

    def showContextMenu(self, pos):
        idx = self.indexAt(pos)
        depth = self.indexDepth(idx)

        if depth > 0:
            layerId = self.model().data(idx if depth == 1 else idx.parent(), Qt.UserRole + 1)
            if layerId is not None:
                if layerId.startswith("pc:"):
                    self.contextMenuPC.exec_(self.mapToGlobal(pos))
                else:
                    self.contextMenu.exec_(self.mapToGlobal(pos))
        else:
            if self.model().itemFromIndex(idx) == self.layerGroupItems[LayerType.POINTCLOUD]:
                self.contextMenuPCG.exec_(self.mapToGlobal(pos))

    def onDoubleClicked(self, _=None):
        idx = self.currentIndex()
        depth = self.indexDepth(idx)

        if depth > 0:
            layer = self.layerFromIndex(idx if depth == 1 else idx.parent())
            self.iface.wnd.showLayerPropertiesDialog(layer)

    def showAddPointCloudLayerDialog(self, _=None):
        self.iface.wnd.showAddPointCloudLayerDialog()

    def removePointCloudLayer(self, _=None):
        data = self.model().data(self.currentIndex(), Qt.UserRole + 1)

        layer = self.iface.settings.getLayer(data)
        if layer is None:
            return

        if QMessageBox.question(self, "Qgis2threejs", "Are you sure you want to remove the layer '{0}' from layer tree?".format(layer.name)) != QMessageBox.Yes:
            return

        self.iface.layerRemoved.emit(layer.layerId)
        self.removeLayer(layer.layerId)

    def clearPointCloudLayers(self):
        parent = self.layerGroupItems[LayerType.POINTCLOUD]
        if parent.hasChildren():
            parent.removeRows(0, parent.rowCount())
