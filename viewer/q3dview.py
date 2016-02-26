# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DView

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
from datetime import datetime
import json
import os

#from PyQt5.Qt import *
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice, QObject, QUrl, Qt, pyqtSlot
from PyQt5.QtGui import QImage
from PyQt5.QtWebKitWidgets import QWebPage, QWebView

import q3dconst
from socketclient import SocketClient


def base64image(image):
  ba = QByteArray()
  buffer = QBuffer(ba)
  buffer.open(QIODevice.WriteOnly)
  image.save(buffer, "PNG")
  return "data:image/png;base64," + ba.toBase64().data().decode("utf-8")


class Bridge(QObject):

  def __init__(self, layerManager, parent=None):
    QObject.__init__(self, parent)
    self.layerManager = layerManager

  @pyqtSlot()
  def myName(self):
    return "QtWebKit Bridge Test"   # Not works

  @pyqtSlot(int, int)
  def setLayerId(self, pyLayerId, jsLayerId):
    self.layerManager.layers[pyLayerId]["jsLayerId"] = jsLayerId
    print("Layer {0} in the layer manager got a layer ID for Q3D project. Layer ID: {1}".format(pyLayerId, jsLayerId))

  @pyqtSlot(str)
  def mouseUp(self, coords):
    print(coords)


class Q3DWebPage(QWebPage):

  def __init__(self, parent=None):
    QWebPage.__init__(self, parent)

    # open log file
    self.logfile = open(os.path.join(os.path.dirname(__file__), "q3dview.log"), "w")

  def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
    print("[JS CONSOLE] {0} ({1}:{2})".format(message, sourceID, lineNumber))
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    self.logfile.write("{0}: {1} ({2}:{3})".format(now, message, sourceID, lineNumber))


class Q3DView(QWebView):

  def __init__(self, parent=None):
    QWebView.__init__(self, parent)

    self.layers = []

    # HTML file and js file for debug
    viewer_dir = os.path.dirname(__file__)
    with open(os.path.join(viewer_dir, "viewer.html"), "r", encoding="UTF-8") as f1:
      with open(os.path.join(viewer_dir, "debug.html"), "w", encoding="UTF-8") as f2:
        f2.write(f1.read().replace("<!--${scripts}-->", '<script src="debug.js"></script>'))

    self.jsfile = open(os.path.join(viewer_dir, "debug.js"), "w")

  def setup(self, wnd, layerManager, pid=""):
    self.wnd = wnd
    self.layerManager = layerManager
    self.iface = SocketClient("Qgis2threejs" + pid, self)
    self.iface.notified.connect(self.notified)
    self.iface.requestReceived.connect(self.requestReceived)
    self.iface.responseReceived.connect(self.responseReceived)

    self._page = Q3DWebPage(self)
    self.setPage(self._page)
    self.loadFinished.connect(self.pageLoaded)

    url = os.path.join(os.path.abspath(os.path.dirname(__file__)), "viewer.html").replace("\\", "/")
    self.setUrl(QUrl.fromLocalFile(url))
    #self.setUrl(QUrl("https://dl.dropboxusercontent.com/u/21526091/qgis-plugins/samples/threejs/mt_fuji.html"))
    print("URL: {0}".format(self.url().toString()))

  def showStatusMessage(self, msg):
    self.wnd.ui.statusbar.showMessage(msg)

  def reload(self):
    pass

  def resetCameraPosition(self):
    pass

  def pageLoaded(self, ok):
    self.bridge = Bridge(self.layerManager, self)
    self._page.mainFrame().addToJavaScriptWindowObject("pyObj", self.bridge)

    self.iface.request(q3dconst.JSON_LAYER_LIST)
    self.iface.request(q3dconst.JS_CREATE_PROJECT)

  def treeItemChanged(self, item):
    itemId = item.data()
    layer = self.layerManager.layers[itemId]
    visible = bool(item.checkState() == Qt.Checked)

    if layer["geomType"] == q3dconst.TYPE_IMAGE:    #TODO: image
      return

    layer["visible"] = visible
    if visible:
      if layer["jsLayerId"] is None:
        self.iface.request(q3dconst.JS_CREATE_LAYER, layer)
      else:
        self.runString("project.layers[{0}].setVisible(true);".format(layer["jsLayerId"]))
        self.iface.request(q3dconst.JS_UPDATE_LAYER, layer)
    else:
      self.runString("project.layers[{0}].setVisible(false);".format(layer["jsLayerId"]))

  def treeItemDoubleClicked(self, index):
    idx = index.data(Qt.UserRole + 1)
    self.iface.notify(q3dconst.N_LAYER_DOUBLECLICKED, self.layerManager.layers[idx])

  def runString(self, string):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    self.jsfile.write("//// runString ({0})\n{1}\n".format(now, string))
    return self._page.mainFrame().evaluateJavaScript(string)

  def notified(self, code, params):
    print("Notification received: {0} ({1})".format(code, str(params)))

    if code == q3dconst.N_CANVAS_EXTENT_CHANGED:
      self.iface.request(q3dconst.JS_UPDATE_PROJECT)

    elif code == q3dconst.N_CANVAS_IMAGE_UPDATED:
      for layer in self.layerManager.layers:
        if layer["visible"]:
          self.iface.request(q3dconst.JS_CREATE_LAYER if layer["jsLayerId"] is None else q3dconst.JS_UPDATE_LAYER, layer)

    elif code == q3dconst.N_LAYER_PROPERTIES_CHANGED:
      layer = self.layerManager.layers[params["id"]]
      layer["properties"] = params["properties"]
      self.iface.request(q3dconst.JS_UPDATE_LAYER, layer)

  def requestReceived(self, dataType, params):
    pass

  def responseReceived(self, data, dataType):
    if dataType == q3dconst.JS_UPDATE_LAYER:
      print("JS_UPDATE_LAYER data received.")
      self.runString(data.data().decode("utf-8"))

    elif dataType == q3dconst.JS_UPDATE_PROJECT:
      print("JS_UPDATE_PROJECT data received.")
      self.runString(data.data().decode("utf-8"))

    elif dataType == q3dconst.JS_CREATE_LAYER:
      print("JS_CREATE_LAYER data received.")
      self.runString(data.data().decode("utf-8"))

    elif dataType == q3dconst.JS_CREATE_PROJECT:
      print("JS_CREATE_PROJECT data received.")
      self.runString(data.data().decode("utf-8"))

    elif dataType == q3dconst.JSON_LAYER_LIST:
      layers = json.loads(data.data().decode("utf-8"))
      for idx, layer in enumerate(layers):
        self.layerManager.addLayer(layer["layerId"], layer["name"], layer["geomType"], idx == 0)

      for layer in self.layerManager.layers:
        if layer["visible"]:
          self.iface.request(q3dconst.JS_CREATE_LAYER, layer)
