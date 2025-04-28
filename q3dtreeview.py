# -*- coding: utf-8 -*-
# (C) 2017 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2017-05-30

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QStandardItemModel, QStandardItem
from qgis.PyQt.QtWidgets import QAction, QMenu, QMessageBox, QTreeView
from qgis.core import QgsApplication

from .conf import PLUGIN_NAME
from .proppages import DEMPropertyPage
from .q3dconst import LayerType


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

    def setup(self, iface, icons):
        self.iface = iface      # Q3DViewerInterface
        self.icons = icons

        model = QStandardItemModel(0, 1)
        self.layerGroupItems = {}
        for typ, name in self.LAYER_GROUP_ITEMS:
            item = QStandardItem(name)
            item.setData(typ)
            item.setIcon(self.icons[typ])
            item.setEditable(False)

            self.layerGroupItems[typ] = item
            model.invisibleRootItem().appendRow([item])

        self.setModel(model)
        self.expandAll()

        self.model().dataChanged.connect(self.treeDataChanged)

        # context menu
        self.actionProperties = QAction("Properties...", self)
        self.actionProperties.triggered.connect(self.onDoubleClicked)

        self.actionRemoveLayer = QAction("Remove from layer tree...", self)
        self.actionRemoveLayer.triggered.connect(self.removeAdditionalLayer)

        self.actionZoomToLayer = QAction("Zoom to layer objects", self)
        self.actionZoomToLayer.triggered.connect(self.zoomToLayer)

        # context menu for map layer
        self.contextMenuLyr = QMenu(self)
        self.contextMenuLyr.addAction(self.actionZoomToLayer)
        self.contextMenuLyr.addAction(self.actionProperties)

        # context menu for flat plane
        self.contextMenuFP = QMenu(self)
        self.contextMenuFP.addAction(self.actionZoomToLayer)
        self.contextMenuFP.addAction(self.actionProperties)
        self.contextMenuFP.addSeparator()
        self.contextMenuFP.addAction(self.actionRemoveLayer)

        # context menu for point cloud layer
        self.contextMenuPC = QMenu(self)
        self.contextMenuPC.addAction(self.actionZoomToLayer)
        self.contextMenuPC.addAction(self.actionProperties)
        self.contextMenuPC.addSeparator()
        self.contextMenuPC.addAction(self.actionRemoveLayer)

        # context menu for DEM material
        self.contextMenuMtl = QMenu(self)
        self.contextMenuMtl.addAction(self.actionProperties)

        # context menu for DEM group
        self.contextMenuDEM = QMenu(self)
        self.contextMenuDEM.addAction(self.iface.wnd.ui.actionAddPlane)

        # context menu for point cloud group
        self.contextMenuPCG = QMenu(self)
        self.contextMenuPCG.addAction(self.iface.wnd.ui.actionAddPointCloudLayer)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)

        self.setExpandsOnDoubleClick(False)
        self.doubleClicked.connect(self.onDoubleClicked)

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

        return item

    def addLayers(self, layers):
        for layer in layers:
            self.addLayer(layer)

    def removeLayer(self, layerId):
        item = self.itemFromLayerId(layerId)
        if item:
            item.parent().removeRow(item.row())

    def clearLayers(self):
        for parent in self.layerGroupItems.values():
            if parent.hasChildren():
                parent.removeRows(0, parent.rowCount())

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

    def updateLayerMaterials(self, layerItem, layer=None):
        layerItem.removeRows(0, layerItem.rowCount())

        layer = layer or self.iface.settings.getLayer(layerItem.data())
        if layer is None or not layer.visible:
            return

        # add material items
        mtls = layer.properties.get("materials", [])
        if not len(mtls):
            return

        currentId = layer.properties.get("mtlId")

        for mtl in mtls:
            id = mtl.get("id")
            item = QStandardItem(mtl.get("name", ""))
            item.setData(id)
            item.setIcon(DEMPropertyPage.iconForMtl(mtl))
            item.setEditable(False)

            if id == currentId:
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            layerItem.appendRow([item])

        self.expand(layerItem.index())

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
                self.iface.buildLayerRequest.emit(layer)

            item = self.model().itemFromIndex(current)
            parent = item.parent()
            font = item.font()
            for row in range(parent.rowCount()):
                font.setBold(row == item.row())
                parent.child(row).setFont(font)

    def treeDataChanged(self, topLeft, bottomRight, roles):
        if Qt.CheckStateRole not in roles:
            return

        # checkbox toggled
        item = self.model().itemFromIndex(topLeft)
        layer = self.iface.settings.getLayer(item.data())
        if layer is None:
            return

        checked = (item.checkState() == Qt.Checked)
        layer.visible = checked
        if layer.visible and not layer.properties:
            layer.properties = self.iface.wnd.getDefaultProperties(layer)

        self.iface.requestBuildLayer(layer)

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
        return depth

    def showContextMenu(self, pos):
        idx = self.indexAt(pos)
        depth = self.indexDepth(idx)

        m = None
        if depth == 1:
            layerId = self.model().data(idx, Qt.UserRole + 1)
            if layerId:
                if layerId.startswith("pc:"):
                    m = self.contextMenuPC
                elif layerId.startswith("fp:"):
                    m = self.contextMenuFP
                else:
                    m = self.contextMenuLyr

        elif depth == 2:
            m = self.contextMenuMtl

        elif depth == 0:
            m = {LayerType.DEM: self.contextMenuDEM,
                 LayerType.POINTCLOUD: self.contextMenuPCG}.get(self.model().data(idx, Qt.UserRole + 1))

        if m:
            m.exec_(self.mapToGlobal(pos))

    def onDoubleClicked(self, _=None):
        idx = self.currentIndex()
        depth = self.indexDepth(idx)

        if depth > 0:
            layer = self.layerFromIndex(idx if depth == 1 else idx.parent())
            self.iface.wnd.showLayerPropertiesDialog(layer)

    def removeAdditionalLayer(self, _=None):
        layer = self.layerFromIndex(self.currentIndex())
        if layer is None:
            return

        if QMessageBox.question(self, PLUGIN_NAME, "Are you sure you want to remove the layer '{0}' from layer tree?".format(layer.name)) != QMessageBox.Yes:
            return

        self.iface.layerRemoved.emit(layer.layerId)
        self.removeLayer(layer.layerId)

    def zoomToLayer(self):
        layer = self.layerFromIndex(self.currentIndex())
        if layer:
            s = "app.cameraAction.zoomToLayer(app.scene.mapLayers[{}])".format(layer.jsLayerId)
            self.iface.wnd.runScript(s, message="zoom to layer '{}'".format(layer.name))
