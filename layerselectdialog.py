# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-04-22

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout
from qgis.core import Qgis, QgsLayerTreeModel, QgsMapLayerProxyModel, QgsProject
from qgis.gui import QgsMapLayerComboBox

from .ui.layerselectdialog import Ui_LayerSelectDialog


class LayerSelectDialog(QDialog):

    def __init__(self, parent):
        QDialog.__init__(self, parent)

        self.mapSettings = None
        self.canvasReady = False    # whether map settings have been applied to map canvas

        # Set up the user interface from Designer.
        self.ui = ui = Ui_LayerSelectDialog()
        ui.setupUi(self)
        ui.tabWidget.setTabEnabled(1, False)
        ui.tabWidget.currentChanged.connect(self.tabPageChanged)

    def initTree(self, visibleLayerIds=None):
        ids = visibleLayerIds or []
        self.root = QgsProject.instance().layerTreeRoot().clone()
        for layer in self.root.findLayers():
            layer.setItemVisibilityChecked(layer.layerId() in ids)

        self.model = QgsLayerTreeModel(self.root)
        self.model.setFlags(QgsLayerTreeModel.AllowNodeChangeVisibility)
        self.ui.treeView.setModel(self.model)

    def setMapSettings(self, mapSettings):
        self.mapSettings = mapSettings
        self.canvasReady = False
        self.ui.tabWidget.setTabEnabled(1, bool(mapSettings))

    def visibleLayers(self):
        layers = []
        for layer in self.root.findLayers():
            if layer.isVisible():
                layers.append(layer.layer())
        return layers

    def visibleLayerIds(self):
        return [layer.id() for layer in self.visibleLayers()]

    def tabPageChanged(self, index):
        if index == 1:
            self.updatePreview()

    def updatePreview(self):
        if self.mapSettings is None:
            return

        if not self.canvasReady:
            c = self.ui.canvas
            s = self.mapSettings

            c.setCanvasColor(s.backgroundColor())
            c.setDestinationCrs(s.destinationCrs())
            c.setRotation(s.rotation())
            c.setExtent(s.extent())

            self.canvasReady = True

        self.ui.canvas.setLayers(self.visibleLayers())


class SingleLayerSelectDialog(QDialog):

    def __init__(self, parent=None, label=""):

        QDialog.__init__(self, parent)

        vl = QVBoxLayout()
        if label:
            vl.addWidget(QLabel(label))

        self.comboBox = QgsMapLayerComboBox()
        if Qgis.QGIS_VERSION_INT < 33400:
            self.comboBox.setFilters(QgsMapLayerProxyModel.HasGeometry | QgsMapLayerProxyModel.RasterLayer | QgsMapLayerProxyModel.MeshLayer)
        else:
            self.comboBox.setFilters(Qgis.LayerFilters(Qgis.LayerFilter.HasGeometry | Qgis.LayerFilter.RasterLayer | Qgis.LayerFilter.MeshLayer))

        vl.addWidget(self.comboBox)

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        vl.addWidget(self.buttonBox)

        self.setLayout(vl)

    def selectedLayer(self):
        return self.comboBox.currentLayer()
