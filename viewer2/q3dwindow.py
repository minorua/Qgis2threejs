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
from PyQt5.QtCore import QObject, QVariant, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

from qgis.core import QgsProject

from .ui5_q3dwindow import Ui_Q3DWindow
from .ui5_propertiesdialog import Ui_PropertiesDialog
from . import q3dconst
from Qgis2threejs.propertypages import DEMPropertyPage, VectorPropertyPage
from Qgis2threejs.qgis2threejstools import logMessage
from Qgis2threejs.vectorobject import objectTypeManager

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

  def addLayer(self, layerId, name, geomType, visible=True, properties=None):
    itemId = len(self.layers)

    self.layers.append({
      "id": itemId,
      "layerId": layerId,
      "name": name,
      "geomType": geomType,
      "visible": visible,
      "properties": properties or json.loads(q3dconst.DEFAULT_PROPERTIES[geomType]),
      "jsLayerId": layerId[:8] + str(itemId)
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


class Q3DViewerInterface:   #:TODO: base on QObject

  def __init__(self, controller, wnd, webView):
    self.controller = controller
    self.wnd = wnd
    self.webView = webView

  def fetchLayerList(self):
    self.wnd.setLayerList(self.controller.getLayerList())

  def startApplication(self):
    self.webView.runString("app.start();");

  def createProject(self):
    # create a scene with lights
    self.controller.createScene()

    #writer.writeProject()
    #self.buf.write("app.loadProject(project);")
    #self.flush()

  def createLayer(self, layer):
    self.controller.createLayer(layer)

  def updateLayer(self, layer):
    self.controller.updateLayer(layer)

  def loadJSONObject(self, obj):
    # display the content of the object in the debug element
    self.webView.runString("document.getElementById('debug').innerHTML = '{}';".format(str(obj)[:1000].replace("'", "\\'")))
    self.webView.bridge.sendData.emit(QVariant(obj))

    #self.webView.runString("var jsonToLoad = JSON.parse('" + json.dumps(obj).replace("'", "\\'") + "');")
    #self.webView.runString("app.loadJSONObject(jsonToLoad);")

  def canvasUpdated(self, painter):
    #self.iface.notify({"code": q3dconst.N_CANVAS_IMAGE_UPDATED})

    for layer in self.wnd.layerManager.layers:
      if layer["visible"]:
        self.updateLayer(layer)
        #self.iface.request({"dataType": q3dconst.JS_UPDATE_LAYER, "layer": layer})

  def canvasExtentChanged(self):
    #self.iface.notify({"code": q3dconst.N_CANVAS_EXTENT_CHANGED})
    self.controller.updateMapCanvasExtent()


class Q3DWindow(QMainWindow):

  def __init__(self, qgisIface, isViewer=True, parent=None, controller=None):   #TODO: controller is required
    QMainWindow.__init__(self, parent)
    self.qgisIface = qgisIface
    self.isViewer = isViewer
    self.settings = controller.settings

    #if live_in_another_process:
    #  self.iface = SocketClient(serverName, self)
    #  self.iface.notified.connect(self.notified)
    #  self.iface.requestReceived.connect(self.requestReceived)
    #  self.iface.responseReceived.connect(self.responseReceived)
    #else:
    #  self.iface = Q3DConnector(self)

    self.ui = Ui_Q3DWindow()
    self.ui.setupUi(self)

    self.layerManager = LayerManager(self.ui.treeView, self)
    self.iface = Q3DViewerInterface(controller, self, self.ui.webView)
    self.ui.webView.setup(self, self.iface, self.layerManager, isViewer)

    # signal-slot connections
    self.ui.actionReset_Camera_Position.triggered.connect(self.ui.webView.resetCameraPosition)
    self.ui.actionAlways_on_Top.toggled.connect(self.alwaysOnTopToggled)
    self.ui.treeView.model().itemChanged.connect(self.treeItemChanged)
    self.ui.treeView.doubleClicked.connect(self.treeItemDoubleClicked)

    self.alwaysOnTopToggled(False)

  def alwaysOnTopToggled(self, checked):
    if checked:
      self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
    else:
      self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
    self.show()

  def treeItemChanged(self, item):
    itemId = item.data()
    layer = self.layerManager.layers[itemId]
    visible = bool(item.checkState() == Qt.Checked)

    if layer["geomType"] == q3dconst.TYPE_IMAGE:    #TODO: image
      return

    layer["visible"] = visible
    if visible:
      if layer["jsLayerId"] is None:
        self.iface.createLayer(layer)
        #self.iface.request({"dataType": q3dconst.JS_CREATE_LAYER, "layer": layer})
      else:
        self.iface.updateLayer(layer)
        #self.runString("project.layers[{0}].setVisible(true);".format(layer["jsLayerId"]))
        #self.iface.request({"dataType": q3dconst.JS_UPDATE_LAYER, "layer": layer})
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
    #TODO: open layer properties dialog
    index = modelIndex.data(Qt.UserRole + 1)
    layer = self.layerManager.layers[index]     #TODO: index or layerId
    mapLayer = QgsProject.instance().mapLayer(layer["layerId"])    #TODO: plugin dem data provider
    if mapLayer is None:
      return

    #treeItem = self.layerManager.model.itemFromIndex(modelIndex)

    dialog = PropertiesDialog(self, self.qgisIface, self.settings)    #, pluginManager)
    dialog.propertiesChanged.connect(self.updateLayerProperties)
    dialog.setLayer(layer["id"], mapLayer, layer["geomType"], layer["properties"])    # TODO: layer -> Layer class?
    dialog.show()
    dialog.exec_()

    #self.iface.notify({"code": q3dconst.N_LAYER_DOUBLECLICKED, "layer": self.layerManager.layers[idx]})

  def updateLayerProperties(self, layerId, properties):
    layer = self.layerManager.layers[layerId]
    layer["properties"] = properties
    if layer["visible"]:
      if layer["jsLayerId"] is None:
        self.iface.createLayer(layer)
      else:
        self.iface.updateLayer(layer)

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

  def printConsoleMessage(self, message, lineNumber, sourceID):
    self.ui.listWidgetDebugView.addItem("{} ({}): {}".format(sourceID.split("/")[-1], lineNumber, message))

  def runString(self, string):
    self.ui.webView.runString(string)

  def setLayerList(self, layers):
    #if os.name == "nt":
    #  data = data.replace(b"\0", b"")   # remove \0 characters at the end  #TODO: why \0 characters there?

    for idx, layer in enumerate(layers):
      logMessage(str(layer))
      self.layerManager.addLayer(layer["layerId"], layer["name"], layer["geomType"], False, layer.get("properties"))    #TODO: check "visible"

    #for layer in self.layerManager.layers:
    #  if layer["visible"]:
    #    self.iface.request({"dataType": q3dconst.JS_CREATE_LAYER, "layer": layer})


class PropertiesDialog(QDialog):

  propertiesChanged = pyqtSignal(int, dict)

  def __init__(self, parent, qgisIface, settings, pluginManager=None):
    QDialog.__init__(self, parent)
    self.iface = qgisIface
    self.pluginManager = pluginManager
    self.mapTo3d = settings.mapTo3d

    self.currentItem = None
    self.mapTool = None   #TODO

    # Set up the user interface from Designer.
    self.ui = Ui_PropertiesDialog()
    self.ui.setupUi(self)
    self.ui.buttonBox.clicked.connect(self.buttonClicked)

    #self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
    #self.activateWindow()

  def setLayer(self, id, mapLayer, geomType, properties=None):
    self.layerId = id
    self.layer = mapLayer
    self.geomType = geomType
    self.properties = properties or {}

    self.setWindowTitle("Layer Properties - {0} (Qgis2threejs)".format(mapLayer.name()))

    if geomType == q3dconst.TYPE_DEM:
      self.page = DEMPropertyPage(self, self)
      self.page.setup(properties, mapLayer, False)
    elif geomType == q3dconst.TYPE_IMAGE:
      return
    else:
      self.page = VectorPropertyPage(self, self)
      self.page.setup(properties, mapLayer)
    self.ui.scrollArea.setWidget(self.page)

  def buttonClicked(self, button):
    role = self.ui.buttonBox.buttonRole(button)
    if role in [QDialogButtonBox.AcceptRole, QDialogButtonBox.ApplyRole]:
      self.propertiesChanged.emit(self.layerId, self.page.properties())

  def createRubberBands(baseExtent, quadtree):
    pass

  def clearRubberBands(self):
    pass

  def startPointSelection(self):
    pass

  def endPointSelection(self):
    pass

  def primaryDEMChanged(self, layerId):
    pass
