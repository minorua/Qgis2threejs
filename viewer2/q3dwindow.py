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
from xml.dom import minidom

from PyQt5.Qt import QMainWindow, QEvent, Qt
from PyQt5.QtCore import QObject, QSettings, QVariant, pyqtSignal
from PyQt5.QtWidgets import QCheckBox, QDialog, QDialogButtonBox

from qgis.core import QgsProject

from .ui5_propertiesdialog import Ui_PropertiesDialog
from .ui5_q3dwindow import Ui_Q3DWindow
from . import q3dconst
from Qgis2threejs.propertypages import DEMPropertyPage, VectorPropertyPage
from Qgis2threejs.qgis2threejstools import logMessage


class Q3DViewerInterface(QObject):

  def __init__(self, parent, qgisIface, treeView, webView, controller):
    QObject.__init__(self, parent)

    self.wnd = parent
    self.qgisIface = qgisIface
    self.treeView = treeView
    self.webView = webView
    self.controller = controller

    # for Rendering checkbox
    self.enabled = True
    self.extentUpdated = False

  def fetchLayerList(self):
    self.wnd.setLayerList(self.controller.getLayerList())

  def startApplication(self):
    self.webView.runString("app.start();");

  def setEnabled(self, enabled):
    self.enabled = enabled
    self.webView.runString("app.resume();" if enabled else "app.pause();");
    if enabled:
      # update layers
      for layerId, layer in enumerate(self.treeView.layers):
        if layer.get("updated", False) or (self.extentUpdated and layer.get("visible", False)):
          self.exportLayer(layer)

      self.extentUpdated = False

  def loadJSONObject(self, obj):
    # display the content of the object in the debug element
    self.webView.runString("document.getElementById('debug').innerHTML = '{}';".format(str(obj)[:500].replace("'", "\\'")))
    self.webView.bridge.sendData.emit(QVariant(obj))

    #self.webView.runString("var jsonToLoad = JSON.parse('" + json.dumps(obj).replace("'", "\\'") + "');")
    #self.webView.runString("app.loadJSONObject(jsonToLoad);")

  def exportScene(self):
    # create a scene with lights
    self.controller.exportScene()

  def exportLayer(self, layer):
    if not self.enabled:
      return
    self.controller.exportLayer(layer)
    layer["updated"] = False

  def canvasUpdated(self, painter):
    if not self.enabled:
      return

    #self.iface.notify({"code": q3dconst.N_CANVAS_IMAGE_UPDATED})
    for layer in self.treeView.layers:
      if layer["visible"]:
        self.exportLayer(layer)
        #self.iface.request({"dataType": q3dconst.JS_UPDATE_LAYER, "layer": layer})
    self.extentUpdated = False

  def canvasExtentChanged(self):
    #self.iface.notify({"code": q3dconst.N_CANVAS_EXTENT_CHANGED})
    # update extent of export settings
    self.controller.updateMapCanvasExtent()
    self.extentUpdated = True

  def showLayerPropertiesDialog(self, layer):
    mapLayer = QgsProject.instance().mapLayer(layer["layerId"])    #TODO: plugin dem data provider
    if mapLayer is None:
      return False

    dialog = PropertiesDialog(self.wnd, self.qgisIface, self.controller.settings)    #, pluginManager)
    dialog.propertiesAccepted.connect(self.updateLayerProperties)
    dialog.setLayer(layer["id"], mapLayer, layer["geomType"], layer["properties"])    # TODO: layer -> Layer class?
    dialog.show()
    dialog.exec_()
    return True

  def updateLayerProperties(self, layerId, properties):
    # save layer properties
    layer = self.treeView.layers[layerId]
    layer["properties"] = properties
    layer["updated"] = True

    if not self.enabled:
      return

    if layer["visible"]:
      self.exportLayer(layer)


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

    self.iface = Q3DViewerInterface(self, qgisIface, self.ui.treeView, self.ui.webView, controller)
    controller.setViewerInterface(self.iface)

    self.setupMenu()
    self.setupStatusBar(self.iface)
    self.ui.treeView.setup(self.iface)
    self.ui.webView.setup(self, self.iface, self.ui.treeView, isViewer)

    self.iface.fetchLayerList()   # self.setLayerList(layers) will be called

    # signal-slot connections
    self.ui.actionReset_Camera_Position.triggered.connect(self.ui.webView.resetCameraPosition)
    self.ui.actionReload.triggered.connect(self.ui.webView.reloadPage)
    self.ui.actionAlways_on_Top.toggled.connect(self.alwaysOnTopToggled)
    self.ui.lineEditInputBox.returnPressed.connect(self.runInputBoxString)

    qgisIface.mapCanvas().renderComplete.connect(self.iface.canvasUpdated)
    qgisIface.mapCanvas().extentsChanged.connect(self.iface.canvasExtentChanged)

    # to disconnect from map canvas when window is closed
    self.setAttribute(Qt.WA_DeleteOnClose)

    self.alwaysOnTopToggled(False)

    # restore window geometry and dockwidget layout
    settings = QSettings()
    self.restoreGeometry(settings.value("/Qgis2threejs/wnd/geometry", b""))
    self.restoreState(settings.value("/Qgis2threejs/wnd/state", b""))

  def closeEvent(self, event):
    settings = QSettings()
    settings.setValue("/Qgis2threejs/wnd/geometry", self.saveGeometry())
    settings.setValue("/Qgis2threejs/wnd/state", self.saveState())
    QMainWindow.closeEvent(self, event)

  def setupMenu(self):
    self.ui.menuPanels.addAction(self.ui.dockWidgetProperties.toggleViewAction())
    self.ui.menuPanels.addAction(self.ui.dockWidgetConsole.toggleViewAction())

  def setupStatusBar(self, iface):
    w = QCheckBox(self.ui.statusbar)
    w.setObjectName("checkBoxRendering")
    w.setText("Rendering")     #_translate("Q3DWindow", "Rendering"))
    w.setChecked(True)
    self.ui.statusbar.addPermanentWidget(w)
    self.ui.checkBoxRendering = w
    self.ui.checkBoxRendering.toggled.connect(iface.setEnabled)

  def alwaysOnTopToggled(self, checked):
    if checked:
      self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
    else:
      self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
    self.show()

  def changeEvent(self, event):
    if self.isViewer and event.type() == QEvent.WindowStateChange:
      if self.windowState() & Qt.WindowMinimized:
        self.runString("app.pause();")
      else:
        self.runString("app.resume();")

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

  def clearConsole(self):
    self.ui.listWidgetDebugView.clear()

  def printConsoleMessage(self, message, lineNumber="", sourceID=""):
    self.ui.listWidgetDebugView.addItem("{} ({}): {}".format(sourceID.split("/")[-1], lineNumber, message))

  def runInputBoxString(self):
    self.runString(self.ui.lineEditInputBox.text())

  def runString(self, string):
    self.ui.webView.runString(string)

  def setLayerList(self, layers):
    #if os.name == "nt":
    #  data = data.replace(b"\0", b"")   # remove \0 characters at the end  #TODO: why \0 characters there?

    for idx, layer in enumerate(layers):
      logMessage(str(layer))
      self.ui.treeView.addLayer(layer["layerId"], layer["name"], layer["geomType"], False, layer.get("properties"))    #TODO: check "visible"

    #for layer in self.ui.treeView.layers:
    #  if layer["visible"]:
    #    self.iface.request({"dataType": q3dconst.JS_CREATE_LAYER, "layer": layer})


class PropertiesDialog(QDialog):

  propertiesAccepted = pyqtSignal(int, dict)

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
      self.propertiesAccepted.emit(self.layerId, self.page.properties())

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
