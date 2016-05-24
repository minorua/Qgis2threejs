# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DWindow

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
from xml.dom import minidom

from PyQt5.Qt import QMainWindow, QEvent, Qt
from PyQt5.QtCore import QObject
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from .ui5_q3dwindow import Ui_Q3DWindow
from . import q3dconst


class LayerManager(QObject):

  def __init__(self, treeView, parent=None):
    QObject.__init__(self, parent)

    self.treeView = treeView
    self.layers = []
    self._index = -1
    self.setupTreeView()

  def setupTreeView(self):
    headers = ["Layer"]
    self.model = QStandardItemModel(0, len(headers))
    self.model.setHorizontalHeaderLabels(headers)

    self.treeView.setModel(self.model)
    #self.treeView.header().setResizeMode(QHeaderView.ResizeToContents)
    #self.treeView.expandAll()

  def nextLayerIndex(self):
    self._index += 1
    return self._index

  def addLayer(self, layerId, name, geomType, visible=True, properties=None):
    itemId = len(self.layers)
    self.layers.append({
      "id": itemId,
      "layerId": layerId,
      "name": name,
      "geomType": geomType,
      "visible": visible,
      "properties": properties or json.loads(q3dconst.DEFAULT_PROPERTIES[geomType]),
      "jsLayerId": None
    })
    geomTypeStr = {
      q3dconst.TYPE_DEM: "DEM",
      q3dconst.TYPE_POINT: "PT",
      q3dconst.TYPE_LINESTRING: "LINE",
      q3dconst.TYPE_POLYGON: "POLY"
      #q3dconst.TYPE_IMAGE: "IMG"
    }[geomType]

    # add layer to tree view
    item = QStandardItem("[{0}] {1}".format(geomTypeStr, name))
    item.setCheckable(True)
    item.setCheckState(Qt.Checked if visible else Qt.Unchecked)
    item.setData(itemId)
    item.setEditable(False)
    self.model.invisibleRootItem().appendRow([item])

  def removeLayer(self, id):
    for index, layer in enumerate(self.layers):
      if layer["id"] == id:
        self.layers[index] = None
        return True
    return False


class Q3DWindow(QMainWindow):

  def __init__(self, serverName, isViewer=True, parent=None):
    QMainWindow.__init__(self, parent)
    self.isViewer = isViewer
    self.ui = Ui_Q3DWindow()
    self.ui.setupUi(self)
    self.layerManager = LayerManager(self.ui.treeView, self)
    self.ui.webView.setup(self, self.layerManager, serverName, isViewer)

    # signal-slot connections
    self.ui.actionReset_Camera_Position.triggered.connect(self.resetCameraPosition)
    self.ui.actionAlways_on_Top.toggled.connect(self.alwaysOnTopToggled)
    self.ui.treeView.model().itemChanged.connect(self.ui.webView.treeItemChanged)
    self.ui.treeView.doubleClicked.connect(self.ui.webView.treeItemDoubleClicked)

    self.alwaysOnTopToggled(isViewer)

  def resetCameraPosition(self):
    self.runString("app.controls.reset();")

  def alwaysOnTopToggled(self, checked):
    if checked:
      self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
    else:
      self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
    self.show()

  def changeEvent(self, event):
    if self.isViewer and event.type() == QEvent.WindowStateChange:
      if self.windowState() & Qt.WindowMinimized:
        # pause application
        self.runString("app.pause();")
      else:
        # start application if not running
        self.runString("if (!app.running) app.start();")

  #TODO: CopyAction is not possible
  def dragEnterEvent(self, event):
    print(str(event.mimeData().formats()))
    if event.mimeData().hasFormat("application/qgis.layertreemodeldata"):
      event.setDropAction(Qt.CopyAction)
      event.accept()
      # event.acceptProposedAction()

  def dropEvent(self, event):
    print("Possible actions: ".format(int(event.possibleActions()))) # => 2 (Qt.MoveAction)
    event.setDropAction(Qt.CopyAction)
    event.accept()
    #event.ignore()
    #event.setAccepted(False)
    xml = event.mimeData().data("application/qgis.layertreemodeldata").data()
    print(xml)
    # b'<layer_tree_model_data>\n <layer-tree-layer expanded="1" checked="Qt::Checked" id="\xe6\xa8\x99\xe6\xba\x96\xe5\x9c\xb0\xe5\x9b\xb320160213181331361" name="\xe6\xa8\x99\xe6\xba\x96\xe5\x9c\xb0\xe5\x9b\xb3">\n  <customproperties/>\n </layer-tree-layer>\n</layer_tree_model_data>\n'

    doc = minidom.parseString(xml)
    layerId = doc.getElementsByTagName("layer-tree-layer")[0].getAttribute("id")
    print("Layer {0} has been dropped.".format(layerId))
    """
    from PyQt5.QtXml import QDomDocument
    # ImportError: No module named 'PyQt5.QtXml'

    doc = QDomDocument()
    doc.setContent(xml)
    root = doc.documentElement()
    layerId = root.firstChild().toElement().attribute("id").decode("utf-8")
    """

  def runString(self, string):
    self.ui.webView.runString(string)
