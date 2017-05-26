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
from PyQt5.QtCore import Qt, QByteArray, QBuffer, QIODevice, QObject, QSize, QUrl, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage, QPainter, QPalette
from PyQt5.QtWebKitWidgets import QWebPage, QWebView

from Qgis2threejs.settings import live_in_another_process


def base64image(image):
  ba = QByteArray()
  buffer = QBuffer(ba)
  buffer.open(QIODevice.WriteOnly)
  image.save(buffer, "PNG")
  return "data:image/png;base64," + ba.toBase64().data().decode("ascii")


class Bridge(QObject):

  sendData = pyqtSignal("QVariant")

  def __init__(self, layerManager, parent=None):
    QObject.__init__(self, parent)
    self._parent = parent
    self.layerManager = layerManager

  @pyqtSlot(int, int, result=str)
  def mouseUpMessage(self, x, y):
    return "Clicked at ({0}, {1})".format(x, y)

  @pyqtSlot(result="QImage")
  def image(self):
    image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.png")
    return QImage(image_path)

  @pyqtSlot(int, int)
  def setLayerId(self, pyLayerId, jsLayerId):   # TODO: set jsLayerId when the layer is added to layer manager.
    self.layerManager.layers[pyLayerId]["jsLayerId"] = jsLayerId
    self._parent.layerCreated(pyLayerId, jsLayerId)
    print("Layer {0} in the layer manager got a layer ID for Q3D project. Layer ID: {1}".format(pyLayerId, jsLayerId))

  @pyqtSlot(int, int, str, int, int, bool)
  def saveImage(self, width, height, dataUrl, tx, ty, intermediate):
    self._parent.saveImage(width, height, dataUrl, tx, ty, intermediate)

  @pyqtSlot(str)
  def mouseUp(self, coords):
    print(coords)


class Q3DWebPage(QWebPage):

  consoleMessage = pyqtSignal(str, int, str)

  def __init__(self, parent=None):
    QWebPage.__init__(self, parent)

    # open log file
    self.logfile = open(os.path.join(os.path.dirname(__file__), "q3dview.log"), "w")

  def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
    self.consoleMessage.emit(message, lineNumber, sourceID)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    self.logfile.write("{} {} ({}: {})\n".format(now, message, sourceID, lineNumber))
    self.logfile.flush()


class Q3DView(QWebView):

  def __init__(self, parent=None):
    QWebView.__init__(self, parent)

    self.requestQueue = []
    self.isProcessingExclusively = False

  def setup(self, wnd, iface, layerManager, isViewer=True):
    self.wnd = wnd
    self.iface = iface
    self.layerManager = layerManager
    self.isViewer = isViewer

    self._page = Q3DWebPage(self)
    self._page.consoleMessage.connect(wnd.printConsoleMessage)
    self._page.mainFrame().javaScriptWindowObjectCleared.connect(self.addJSObject)
    self.loadFinished.connect(self.pageLoaded)
    self.setPage(self._page)

    if not isViewer:
      # transparent background
      palette = self._page.palette()
      palette.setBrush(QPalette.Base, Qt.transparent)
      self._page.setPalette(palette)
      self.setAttribute(Qt.WA_OpaquePaintEvent, False)

    self.renderId = None    # for renderer

    filetitle = "viewer" if isViewer else "layer"
    url = os.path.join(os.path.abspath(os.path.dirname(__file__)), filetitle + ".html").replace("\\", "/")
    self.setUrl(QUrl.fromLocalFile(url))
    #self.setUrl(QUrl("https://dl.dropboxusercontent.com/u/21526091/qgis-plugins/samples/threejs/mt_fuji.html"))
    print("URL: {0}".format(self.url().toString()))

  def addJSObject(self):
    self.bridge = Bridge(self.layerManager, self)
    self._page.mainFrame().addToJavaScriptWindowObject("pyObj", self.bridge)

  def pageLoaded(self, ok):
    self.runString("pyObj.sendData.connect(this, dataReceived);")

    self.iface.fetchLayerList()   # wnd.setLayerList(layers) will be called
    #TODO: move to window?

    #self.iface.request({"dataType": q3dconst.JSON_LAYER_LIST})
    if self.isViewer:
      self.iface.createProject()
      self.iface.startApplication()
      #self.iface.request({"dataType": q3dconst.JS_CREATE_PROJECT})
      #self.iface.request({"dataType": q3dconst.JS_START_APP})
    else:
      self.iface.request({"dataType": q3dconst.JS_INITIALIZE})

  def showStatusMessage(self, msg):
    self.wnd.ui.statusbar.showMessage(msg)

  def reload(self):
    pass

  def resetCameraPosition(self):
    self.runString("app.controls.reset();")

  def runBytes(self, ba):
    if os.name == "nt":
      ba = ba.replace(b"\0", b"")   # remove \0 characters at the end  #TODO: why \0 characters there?
    self.runString(ba.decode("utf-8"))

  def runString(self, string):
    self.wnd.ui.listWidgetDebugView.addItem("runString: {} // and app.render();".format(string))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    self._page.logfile.write("{} runString: {}\n".format(now, string))
    self._page.logfile.flush()

    # string += "\nfor(var xxx = 0; xxx < 9999999999; xxx++) { var i = 9999 / 0.5; };"
    string += "\napp.render();"   #TODO: THIS IS FOR DEBUG
    return self._page.mainFrame().evaluateJavaScript(string)

  def saveImage(self, width, height, dataUrl="", tx=0, ty=0, intermediate=False):
    image = None
    if dataUrl:
      ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
      if tx or ty:
        image = QImage()
        image.loadFromData(ba)

    else:
      image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
      painter = QPainter(image)
      self._page.mainFrame().render(painter)
      painter.end()

    if tx or ty:
      img = QImage(width - tx, height - ty, QImage.Format_ARGB32_Premultiplied)
      painter = QPainter(img)
      painter.drawImage(tx, ty, image)
      painter.end()
      image = img

    # image to byte array
    if image:
      ba = QByteArray()
      buf = QBuffer(ba)
      buf.open(QIODevice.WriteOnly)
      image.save(buf, "PNG")

    dataType = q3dconst.BIN_INTERMEDIATE_IMAGE if intermediate else q3dconst.BIN_SCENE_IMAGE
    self.iface.respond(ba.data(), {"dataType": dataType, "renderId": self.renderId})    # q3dconst.FORMAT_BINARY
