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

from PyQt5.QtCore import (QByteArray, QBuffer, QDir, QEventLoop, QIODevice, QObject, QSize, QTimer, QUrl, QVariant,
                          pyqtSignal, pyqtSlot, qDebug)
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QFileDialog, QMessageBox
try:
    from PyQt5.QtWebKit import QWebSettings, QWebSecurityOrigin
    from PyQt5.QtWebKitWidgets import QWebPage, QWebView
except ModuleNotFoundError:
    if os.name == "posix":
        QMessageBox.warning(None, "Qgis2threejs", 'Missing dependencies related to PyQt5 and QtWebKit. Please install "python3-pyqt5.qtwebkit" package (Debian/Ubuntu) before using this plugin.')
    raise

from .conf import DEBUG_MODE
from .qgis2threejstools import js_bool, logMessage, pluginDir


def base64image(image):
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return "data:image/png;base64," + ba.toBase64().data().decode("ascii")


class Bridge(QObject):

    # Python to Python signals
    sceneLoaded = pyqtSignal()
    sceneLoadError = pyqtSignal()
    statusMessage = pyqtSignal(str, int)
    modelDataReady = pyqtSignal("QByteArray", str)
    imageReady = pyqtSignal(int, int, "QImage")

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

    @pyqtSlot()
    def onSceneLoadError(self):
        self.sceneLoadError.emit()

    @pyqtSlot(int, int, result=str)
    def mouseUpMessage(self, x, y):
        return "Clicked at ({0}, {1})".format(x, y)
        # JS side: console.log(pyObj.mouseUpMessage(e.clientX, e.clientY));

    @pyqtSlot(str, int)
    def showStatusMessage(self, message, duration=0):
        self.statusMessage.emit(message, duration)

    @pyqtSlot("QByteArray", str)
    def saveBytes(self, data, filename):
        self.modelDataReady.emit(data, filename)

    @pyqtSlot(str, str)
    def saveString(self, text, filename):
        self.modelDataReady.emit(text.encode("UTF-8"), filename)

    @pyqtSlot(int, int, str)
    def saveImage(self, width, height, dataUrl):
        image = None
        if dataUrl:
            ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
            image = QImage()
            image.loadFromData(ba)
        self.imageReady.emit(width, height, image)


class Q3DWebPage(QWebPage):

    ready = pyqtSignal()
    sceneLoaded = pyqtSignal()
    sceneLoadError = pyqtSignal()

    def __init__(self, parent=None):
        QWebPage.__init__(self, parent)

        self.modelLoadersLoaded = False

        if DEBUG_MODE == 2:
            # open log file
            self.logfile = open(pluginDir("q3dview.log"), "w")

    def setup(self, settings, wnd=None, exportMode=False):
        """wnd: Q3DWindow or None (off-screen mode)"""
        self.settings = settings
        self.wnd = wnd or DummyWindow()
        self.offScreen = bool(wnd is None)
        self.exportMode = exportMode

        self.bridge = Bridge(self)
        self.bridge.sceneLoaded.connect(self.sceneLoaded)
        self.bridge.sceneLoadError.connect(self.sceneLoadError)
        self.bridge.modelDataReady.connect(self.saveModelData)
        self.bridge.imageReady.connect(self.saveImage)
        if wnd:
            self.bridge.statusMessage.connect(wnd.ui.statusbar.showMessage)

        self.loadFinished.connect(self.pageLoaded)
        self.mainFrame().javaScriptWindowObjectCleared.connect(self.addJSObject)

        # security settings
        origin = self.mainFrame().securityOrigin()
        origin.addAccessWhitelistEntry("http:", "*", QWebSecurityOrigin.AllowSubdomains)
        origin.addAccessWhitelistEntry("https:", "*", QWebSecurityOrigin.AllowSubdomains)

        # if self.offScreen:
        #     # transparent background
        #     palette = self.palette()
        #     palette.setBrush(QPalette.Base, Qt.transparent)
        #     self.setPalette(palette)
        #     #webview: self.setAttribute(Qt.WA_OpaquePaintEvent, False)

        url = os.path.join(os.path.abspath(os.path.dirname(__file__)), "viewer", "viewer.html").replace("\\", "/")
        self.myUrl = QUrl.fromLocalFile(url)
        self.mainFrame().setUrl(self.myUrl)

    def reload(self):
        self.mainFrame().setUrl(self.myUrl)

    def pageLoaded(self, ok):
        self.modelLoadersLoaded = False

        # configuration
        if self.exportMode:
            self.runScript("Q3D.Config.exportMode = true;")

        p = self.settings.decorationProperties("NorthArrow")
        if p.get("visible"):
            self.runScript("Q3D.Config.northArrow.visible = true;")
            self.runScript("Q3D.Config.northArrow.color = {};".format(p.get("color", 0)))

        header = self.settings.headerLabel()
        footer = self.settings.footerLabel()
        if header or footer:
            self.runScript('setHFLabel("{}", "{}");'.format(header.replace('"', '\\"'), footer.replace('"', '\\"')))

        # call init()
        self.runScript("init({}, {}, {});".format(js_bool(self.offScreen),
                                                  js_bool(self.settings.isOrthoCamera()),
                                                  DEBUG_MODE))

        self.ready.emit()

    def runScript(self, string, message="", sourceID="q3dview.py"):
        if DEBUG_MODE:
            self.wnd.printConsoleMessage(message if message else string, sourceID=sourceID)
            qDebug("runScript: {}".format(message if message else string).encode("utf-8"))

            if DEBUG_MODE == 2:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.logfile.write("{} runScript: {}\n".format(now, message if message else string))
                self.logfile.flush()

        return self.mainFrame().evaluateJavaScript(string)

    def addJSObject(self):
        self.mainFrame().addToJavaScriptWindowObject("pyObj", self.bridge)
        if DEBUG_MODE:
            self.wnd.printConsoleMessage("pyObj added", sourceID="q3dview.py")

    def loadScriptFile(self, filename):
        """evaluate a script file without using a script tag to load script synchronously"""
        with open(filename, "r", encoding="utf-8") as f:
            script = f.read()
        return self.runScript(script, "// {} loaded".format(os.path.basename(filename)))

    def loadModelLoaders(self):
        if not self.modelLoadersLoaded:
            self.loadScriptFile(pluginDir("js/threejs/loaders/ColladaLoader.js"))
            self.loadScriptFile(pluginDir("js/threejs/loaders/GLTFLoader.js"))
            self.modelLoadersLoaded = True

    def cameraState(self):
        return self.mainFrame().evaluateJavaScript("cameraState()")

    def setCameraState(self, state):
        """set camera position and camera target"""
        self.bridge.setData(state)
        self.mainFrame().evaluateJavaScript("setCameraState(fetchData())")

    def resetCameraState(self):
        self.runScript("app.controls.reset();")

    def waitForSceneLoaded(self, cancelSignal=None, timeout=None):
        loading = self.mainFrame().evaluateJavaScript("app.loadingManager.isLoading")

        if DEBUG_MODE:
            logMessage("waitForSceneLoaded: loading={}".format(loading), False)

        if not loading:
            return False

        loop = QEventLoop()

        def error():
            loop.exit(1)

        def userCancel():
            loop.exit(2)

        def timeOut():
            loop.exit(3)

        self.sceneLoaded.connect(loop.quit)
        self.sceneLoadError.connect(error)

        if cancelSignal:
            cancelSignal.connect(userCancel)

        if timeout:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(timeOut)
            timer.start(timeout)

        err = loop.exec_()
        if err:
            return {1: "error", 2: "canceled", 3: "timeout"}[err]
        return False

    def sendData(self, data):
        self.bridge.setData(data)
        self.mainFrame().evaluateJavaScript("loadJSONObject(fetchData())")

    def saveModelData(self, data, filename):
        try:
            with open(filename, "wb") as f:
                f.write(data)

            logMessage("Successfully saved model data: " + filename, False)
        except Exception as e:
            QMessageBox.warning(self, "Failed to save model data.", str(e))

    def renderImage(self, width, height):
        old_size = self.viewportSize()
        self.setViewportSize(QSize(width, height))

        image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        self.mainFrame().render(painter)
        painter.end()

        self.setViewportSize(old_size)
        return image

    def saveImage(self, width, height, image):
        filename, _ = QFileDialog.getSaveFileName(self.wnd, self.tr("Save As"), QDir.homePath(), "PNG files (*.png)")
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

        # security settings - allow access to remote urls (for Icon)
        self.settings().setAttribute(QWebSettings.LocalContentCanAccessRemoteUrls, True)

    def setup(self, iface, settings, wnd=None, enabled=True):
        self.iface = iface
        self.wnd = wnd
        self._enabled = enabled     # whether preview is enabled at start

        self._page.ready.connect(self.pageReady)
        self._page.setup(settings, wnd)

    def pageReady(self):
        # start app
        self.runScript("app.start();")

        if self._enabled:
            self.iface.requestSceneUpdate()
        else:
            self.iface.previewStateChanged.emit(False)

    def reloadPage(self):
        self.wnd.clearConsole()
        self._page.reload()

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        # logMessage(event.mimeData().formats())
        for url in event.mimeData().urls():
            filename = url.fileName()
            if filename == "cloud.js":
                self.wnd.addPointCloudLayer(url.toString())
            else:
                self.runScript("loadModel('{}');".format(url.toString()))

        event.acceptProposedAction()

    # def reload(self):
    #  pass

    def sendData(self, data):
        self._page.sendData(data)

    def resetCameraState(self):
        self._page.resetCameraState()

    def runScript(self, string, message="", sourceID="q3dview.py"):
        self._page.runScript(string, message, sourceID)


class DummyWindow:

    def printConsoleMessage(self, message, lineNumber="", sourceID=""):
        logMessage(message, False)
