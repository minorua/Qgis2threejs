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
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QDialog
from qgis.core import QGis, QgsProject
from qgis.gui import QgsMapCanvasLayer

if QGis.QGIS_VERSION_INT >= 20600:
  from qgis.core import QgsLayerTreeModel
else:   # 2.4
  from qgis.gui import QgsLayerTreeModel

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

  def initTree(self, ids=None):
    ids = ids or []
    self.root = QgsProject.instance().layerTreeRoot().clone()
    for layer in self.root.findLayers():
      layer.setVisible(Qt.Checked if layer.layerId() in ids else Qt.Unchecked)

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
      c.setCrsTransformEnabled(s.hasCrsTransformEnabled())
      c.setDestinationCrs(s.destinationCrs())
      if QGis.QGIS_VERSION_INT >= 20700:
        c.setRotation(s.rotation())
      c.setExtent(s.extent())

      self.canvasReady = True

    self.ui.canvas.setLayerSet([QgsMapCanvasLayer(layer) for layer in self.visibleLayers()])
