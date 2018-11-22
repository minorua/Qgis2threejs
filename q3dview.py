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
import os

#from PyQt5.Qt import *
from PyQt5.QtCore import (Qt, QByteArray, QBuffer, QDir, QEventLoop, QIODevice, QObject, QTimer, QUrl, QVariant,
                          pyqtSignal, pyqtSlot, qDebug)
from PyQt5.QtGui import QImage, QPainter, QPalette
from PyQt5.QtWidgets import QFileDialog, QMessageBox
try:
  from PyQt5.QtWebKit import QWebSettings, QWebSecurityOrigin
  from PyQt5.QtWebKitWidgets import QWebPage, QWebView
except ModuleNotFoundError:
  if os.name == "posix":
    QMessageBox.warning(None, "Qgis2threejs", 'Missing dependencies related to PyQt5 and QtWebKit. Please install "python3-pyqt5.qtwebkit" package (Debian/Ubuntu) before using this plugin.')
  raise

from .conf import DEBUG_MODE
from .qgis2threejstools import logMessage, pluginDir

def base64image(image):
  ba = QByteArray()
  buffer = QBuffer(ba)
  buffer.open(QIODevice.WriteOnly)
  image.save(buffer, "PNG")
  return "data:image/png;base64," + ba.toBase64().data().decode("ascii")


class Bridge(QObject):

  # Python to Python signals
  sceneLoaded = pyqtSignal()
  modelDataReceived = pyqtSignal("QByteArray", str)
  imageReceived = pyqtSignal(int, int, "QImage")

  def __init__(self, parent=None):
    QObject.__init__(self, parent)
    self._parent = parent
    self.data = QVariant()

  @pyqtSlot(result="QVariant")
  def data(self):
    return self.data

  def setData(self, data):
    self.data = QVariant(data)

  @pyqtSlot()
  def onSceneLoaded(self):
    self.sceneLoaded.emit()

  @pyqtSlot(int, int, result=str)
  def mouseUpMessage(self, x, y):
    return "Clicked at ({0}, {1})".format(x, y)
    # JS side: console.log(pyObj.mouseUpMessage(e.clientX, e.clientY));

  @pyqtSlot("QByteArray", str)
  def saveBytes(self, data, filename):
    self.modelDataReceived.emit(data, filename)

  @pyqtSlot(str, str)
  def saveString(self, text, filename):
    self.modelDataReceived.emit(text.encode("UTF-8"), filename)

  @pyqtSlot(int, int, str)
  def saveImage(self, width, height, dataUrl):
    image = None
    if dataUrl:
      ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
      image = QImage()
      image.loadFromData(ba)
    self.imageReceived.emit(width, height, image)


class Q3DWebPage(QWebPage):

  initialized = pyqtSignal()
  sceneLoaded = pyqtSignal()

  def __init__(self, parent=None):
    QWebPage.__init__(self, parent)

    self.modelLoadersLoaded = False

    if DEBUG_MODE == 2:
      # open log file
      self.logfile = open(pluginDir("q3dview.log"), "w")

  def setup(self, iface, wnd=None, enabled=True, exportMode=False):
    """iface: Q3DInterface or Q3DViewerInterface
       wnd: Q3DWindow or None (off-screen mode)"""
    self.iface = iface
    self.wnd = wnd or DummyWindow()
    self.offScreen = bool(wnd is None)
    self._enabled = enabled
    self.exportMode = exportMode

    self.bridge = Bridge(self)
    self.bridge.sceneLoaded.connect(self.sceneLoaded)
    self.bridge.modelDataReceived.connect(self.saveModelData)
    self.bridge.imageReceived.connect(self.saveImage)

    self.loadFinished.connect(self.pageLoaded)
    self.mainFrame().javaScriptWindowObjectCleared.connect(self.addJSObject)

    # security settings
    origin = self.mainFrame().securityOrigin()
    origin.addAccessWhitelistEntry("http:", "*", QWebSecurityOrigin.AllowSubdomains)
    origin.addAccessWhitelistEntry("https:", "*", QWebSecurityOrigin.AllowSubdomains)

    if False and self.offScreen:
      # transparent background
      palette = self.palette()
      palette.setBrush(QPalette.Base, Qt.transparent)
      self.setPalette(palette)
      #webview: self.setAttribute(Qt.WA_OpaquePaintEvent, False)

    url = os.path.join(os.path.abspath(os.path.dirname(__file__)), "viewer", "viewer.html").replace("\\", "/")
    self.myUrl = QUrl.fromLocalFile(url)
    self.mainFrame().setUrl(self.myUrl)

  def reload(self):
    self.mainFrame().setUrl(self.myUrl)

  def pageLoaded(self, ok):
    self.modelLoadersLoaded = False

    # start application
    self.iface.startApplication(offScreen=self.offScreen, exportMode=self.exportMode)

    if self.iface.controller.settings.isOrthoCamera():
      self.runString("switchCamera(true);")

    self.initialized.emit()

    if self.offScreen:
      return

    if self._enabled:
      self.iface.updateScene()
    else:
      self.iface.setPreviewEnabled(False)

  def runString(self, string, message="", sourceID="q3dview.py"):
    if DEBUG_MODE:
      self.wnd.printConsoleMessage(message if message else string, sourceID=sourceID)
      qDebug("runString: {}\n".format(message if message else string).encode("utf-8"))

      if DEBUG_MODE == 2:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logfile.write("{} runString: {}\n".format(now, message if message else string))
        self.logfile.flush()

    return self.mainFrame().evaluateJavaScript(string)

  def addJSObject(self):
    self.mainFrame().addToJavaScriptWindowObject("pyObj", self.bridge)
    if DEBUG_MODE:
      self.wnd.printConsoleMessage("pyObj added", sourceID="q3dview.py")

  def loadScriptFile(self, filename):
    with open(filename, "r", encoding="utf-8") as f:
      script = f.read()
    return self.runString(script, "// {} loaded".format(os.path.basename(filename)))

  def loadModelLoaders(self):
    if not self.modelLoadersLoaded:
      self.loadScriptFile(pluginDir("js/polyfill/polyfill.min.js"))
      self.loadScriptFile(pluginDir("js/threejs/loaders/ColladaLoader.js"))
      self.loadScriptFile(pluginDir("js/threejs/loaders/GLTFLoader.js"))
      self.modelLoadersLoaded = True

  def resetCameraPosition(self):
    self.runString("app.controls.reset();")

  def waitForSceneLoaded(self, timeout=None):
    loading = self.mainFrame().evaluateJavaScript("app.loadingManager.isLoading")

    if DEBUG_MODE:
      logMessage("waitForSceneLoaded: loading={}".format(loading), False)

    if not loading:
      return False

    loop = QEventLoop()
    self.sceneLoaded.connect(loop.quit)
    #TODO: self.sceneLoadError.connect(loop.quit)
    #TODO: userCancelSignal.connect(loop.quit)
    if timeout:
      QTimer.singleShot(timeout, loop.quit)
    loop.exec_()

    #TODO:
    # if error:
    #   return err_msg
    return False

  def sendData(self, data):
    self.bridge.setData(data)
    self.mainFrame().evaluateJavaScript("loadJSONObject(fetchData());")

  def saveModelData(self, data, filename):
    try:
      with open(filename, "wb") as f:
        f.write(data)

      logMessage("Successfully saved model data: " + filename, False)
    except Exception as e:
      QMessageBox.warning(self, "Failed to save model data.", str(e))

  def saveImage(self, width, height, image):
    if image is None:
      image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
      painter = QPainter(image)
      self.mainFrame().render(painter)
      painter.end()

    filename, _ = QFileDialog.getSaveFileName(self, self.tr("Save As"), QDir.homePath(), "PNG files (*.png)")
    if filename:
      image.save(filename)

  def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
    self.wnd.printConsoleMessage(message, lineNumber, sourceID)

    if DEBUG_MODE == 2:
      now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      self.logfile.write("{} {} ({}: {})\n".format(now, message, sourceID, lineNumber))
      self.logfile.flush()


class Q3DView(QWebView):

  def __init__(self, parent=None):
    QWebView.__init__(self, parent)
    self.setAcceptDrops(True)

    self._page = Q3DWebPage(self)
    self.setPage(self._page)

  def setup(self, iface, wnd=None, enabled=True):
    self.iface = iface
    self.wnd = wnd
    self._page.setup(iface, wnd, enabled)

    # security settings - allow access to remote urls (for Icon)
    self.settings().setAttribute(QWebSettings.LocalContentCanAccessRemoteUrls, True)

  def reloadPage(self):
    self.wnd.clearConsole()
    self._page.reload()

  def dragEnterEvent(self, event):
    event.acceptProposedAction()

  def dropEvent(self, event):
    # logMessage(event.mimeData().formats())
    for url in event.mimeData().urls():
      self.runString("loadModel('" + url.toString() + "');")

    event.acceptProposedAction()

  #def reload(self):
  #  pass

  def showStatusMessage(self, msg):
    self.wnd.ui.statusbar.showMessage(msg)

  def sendData(self, data):
    self._page.sendData(data)

  def resetCameraPosition(self):
    self._page.resetCameraPosition()

  def runString(self, string, message="", sourceID="q3dview.py"):
    self._page.runString(string, message, sourceID)


class DummyWindow:

  def printConsoleMessage(self, message, lineNumber="", sourceID=""):
    logMessage(message, False)
