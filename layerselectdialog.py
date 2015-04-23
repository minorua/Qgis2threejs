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
from PyQt4.QtGui import QDialog, QFileDialog
from qgis.core import QGis, QgsProject

if QGis.QGIS_VERSION_INT >= 20600:
  from qgis.core import QgsLayerTreeModel
else:   # 2.4
  from qgis.gui import QgsLayerTreeModel

from ui.ui_layerselectdialog import Ui_LayerSelectDialog

class LayerSelectDialog(QDialog):

  def __init__(self, parent):
    QDialog.__init__(self, parent)

    # Set up the user interface from Designer.
    self.ui = ui = Ui_LayerSelectDialog()
    ui.setupUi(self)

    ui.tabWidget.currentChanged.connect(self.tabPageChanged)

  def initTree(self, ids=None):
    ids = ids or []
    self.root = QgsProject.instance().layerTreeRoot().clone()
    for layer in self.root.findLayers():
      layer.setVisible(Qt.Checked if layer.layerId() in ids else Qt.Unchecked)

    self.model = QgsLayerTreeModel(self.root)
    self.model.setFlags(QgsLayerTreeModel.AllowNodeChangeVisibility)
    self.ui.treeView.setModel(self.model)

  def visibleLayers(self):
    layers = []
    for layer in self.root.findLayers():
      if layer.isVisible():
        layers.append(layer.layer())
    return layers

  def tabPageChanged(self, index):
    if index == 1:
      self.updatePreview()

  #TODO
  def updatePreview(self):
    pass
