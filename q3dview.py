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

from PyQt5.QtCore import (Qt, QByteArray, QBuffer, QDir, QEventLoop, QIODevice, QObject, QSize, QTimer, QUrl, QVariant,
                          pyqtSignal, pyqtSlot, qDebug)
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox, QVBoxLayout

from .conf import DEBUG_MODE
try:
    from PyQt5.QtWebKit import QWebSettings, QWebSecurityOrigin
    from PyQt5.QtWebKitWidgets import QWebPage, QWebView
    if DEBUG_MODE:
        from PyQt5.QtWebKitWidgets import QWebInspector
except ModuleNotFoundError:
    if os.name == "posix":
        QMessageBox.warning(None, "Qgis2threejs", 'Missing dependencies related to PyQt5 and QtWebKit. Please install "python3-pyqt5.qtwebkit" package (Debian/Ubuntu) before using this plugin.')
    raise

from .q3dconst import Script
from .tools import js_bool, logMessage, pluginDir


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
    animationStopped = pyqtSignal()

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

    @pyqtSlot()
    def onAnimationStopped(self):
        self.animationStopped.emit()

    """
    @pyqtSlot(int, int, result=str)
    def mouseUpMessage(self, x, y):
        return "Clicked at ({0}, {1})".format(x, y)
        # JS side: console.log(pyObj.mouseUpMessage(e.clientX, e.clientY));
    """


class Q3DWebPage(QWebPage):

    ready = pyqtSignal()
    sceneLoaded = pyqtSignal()
    sceneLoadError = pyqtSignal()

    def __init__(self, parent=None):
        QWebPage.__init__(self, parent)

        self.loadedScripts = {}

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
            self.bridge.animationStopped.connect(wnd.ui.animationPanel.animationStopped)

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
        self.reload()

    def reload(self):
        self.bridge.showStatusMessage("Initializing preview...")
        self.mainFrame().setUrl(self.myUrl)

    def pageLoaded(self, ok):
        self.loadedScripts = {}

        # configuration
        if self.exportMode:
            self.runScript("Q3D.Config.exportMode = true;")

        if self.settings.isOrthoCamera():
            self.runScript("Q3D.Config.orthoCamera = true;")

        p = self.settings.widgetProperties("NorthArrow")
        if p.get("visible"):
            self.runScript("Q3D.Config.northArrow.visible = true;")
            self.runScript("Q3D.Config.northArrow.color = {};".format(p.get("color", 0)))

        # navigation widget
        if not self.settings.isNavigationEnabled():
            self.runScript("Q3D.Config.navigation.enabled = false;")

        # labels
        header = self.settings.headerLabel()
        footer = self.settings.footerLabel()
        if header or footer:
            self.runScript('setHFLabel(pyData());', data={"Header": header, "Footer": footer})

        # call init()
        self.runScript("init({}, {});".format(js_bool(self.offScreen), DEBUG_MODE))

        self.bridge.showStatusMessage("")

        self.ready.emit()

    def runScript(self, string, data=None, message="", sourceID="q3dview.py"):
        if DEBUG_MODE:
            self.wnd.printConsoleMessage(message if message else string, sourceID=sourceID)
            qDebug("runScript: {}".format(message if message else string).encode("utf-8"))

            if DEBUG_MODE == 2:
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.logfile.write("{} runScript: {}\n".format(now, message if message else string))
                self.logfile.flush()

        if data:
            self.bridge.setData(data)

        return self.mainFrame().evaluateJavaScript(string)

    def addJSObject(self):
        self.mainFrame().addToJavaScriptWindowObject("pyObj", self.bridge)
        if DEBUG_MODE:
            self.wnd.printConsoleMessage("pyObj added", sourceID="q3dview.py")

    def loadScriptFile(self, id, force=False):
        """evaluate a script file without using a script tag. script is loaded synchronously"""
        if id in self.loadedScripts and not force:
            return

        filename = pluginDir("js", Script.PATH[id])

        with open(filename, "r", encoding="utf-8") as f:
            script = f.read()

        self.runScript(script, message="{} loaded.".format(os.path.basename(filename)))
        self.loadedScripts[id] = True

    def loadScriptFiles(self, ids, force=False):
        for id in ids:
            self.loadScriptFile(id, force)

    def cameraState(self, flat=False):
        return self.mainFrame().evaluateJavaScript("cameraState({})".format(1 if flat else 0))

    def setCameraState(self, state):
        """set camera position and camera target"""
        self.bridge.setData(state)
        self.mainFrame().evaluateJavaScript("setCameraState(pyData())")

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
        self.mainFrame().evaluateJavaScript("loadJSONObject(pyData())")

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

        # security setting for Icon, Model File and point cloud layer
        self.settings().setAttribute(QWebSettings.LocalContentCanAccessRemoteUrls, True)

        # web inspector setting
        if DEBUG_MODE:
            self.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)

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
            if filename in ("cloud.js", "ept.json"):
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

    def runScript(self, string, data=None, message="", sourceID="q3dview.py"):
        return self._page.runScript(string, data, message, sourceID)

    def showInspector(self):
        dlg = QDialog(self)
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.resize(800, 500)
        dlg.setWindowTitle("Qgis2threejs Web Inspector")

        wi = QWebInspector(dlg)
        wi.setPage(self._page)

        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(wi)

        dlg.setLayout(v)
        dlg.show()
        dlg.exec_()

    def showJSInfo(self):
        info = self.runScript("app.renderer.info")
        QMessageBox.information(self, "three.js Renderer Info", str(info))

    def clearCaches(self):
        QWebSettings.clearMemoryCaches()


class DummyWindow:

    def printConsoleMessage(self, message, lineNumber="", sourceID=""):
        logMessage(message, False)
