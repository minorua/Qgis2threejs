# -*- coding: utf-8 -*-
"""
/***************************************************************************
 LayerSelectDialog
                             -------------------
        begin                : 2015-04-22
        copyright            : (C) 2015 Minoru Akagi
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
from PyQt5.QtWidgets import QDialog
from qgis.core import QgsLayerTreeModel, QgsProject

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
