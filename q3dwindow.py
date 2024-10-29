# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import os
from datetime import datetime

from PyQt5.QtCore import Qt, QDir, QEvent, QEventLoop, QObject, QSettings, QThread, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices, QIcon
from PyQt5.QtWidgets import (QAction, QActionGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                             QFileDialog, QMainWindow, QMenu, QMessageBox, QProgressBar, QStyle, QToolButton)
from qgis.core import Qgis, QgsProject, QgsApplication

from .conf import DEBUG_MODE, RUN_CNTLR_IN_BKGND, PLUGIN_NAME, PLUGIN_VERSION
from .exportsettings import ExportSettings
from .pluginmanager import pluginManager
from .proppages import ScenePropertyPage, DEMPropertyPage, VectorPropertyPage, PointCloudPropertyPage
from .q3dcore import Layer
from .q3dconst import LayerType, Script
from .q3dcontroller import Q3DController
from .q3dinterface import Q3DInterface
from . import q3dview
from .q3dview import WEBENGINE_AVAILABLE, WEBKIT_AVAILABLE, WEBVIEWTYPE_WEBENGINE, setCurrentWebView
from . import utils
from .utils import createUid, hex_color, logMessage, pluginDir, Correspondent
from .ui.propertiesdialog import Ui_PropertiesDialog
from .ui import q3dwindow as ui_wnd
from .ui.q3dwindow import Ui_Q3DWindow


class Q3DViewerInterface(Q3DInterface):

    abortRequest = pyqtSignal(bool)                  # param: cancel all requests in queue
    buildSceneRequest = pyqtSignal(object, bool, bool)    # params: scene properties dict (None if properties do not changes), update all, reload
    buildLayerRequest = pyqtSignal(Layer)           # param: Layer object
    updateWidgetRequest = pyqtSignal(str, dict)      # params: widget name (e.g. Navi, NorthArrow, Label), properties dict
    runScriptRequest = pyqtSignal(str, object)       # params: script, data to send to web page

    updateExportSettingsRequest = pyqtSignal(ExportSettings)    # param: export settings
    cameraChanged = pyqtSignal(bool)                 # params: is ortho camera
    navStateChanged = pyqtSignal(bool)               # param: enabled
    previewStateChanged = pyqtSignal(bool)           # param: enabled
    layerAdded = pyqtSignal(Layer)                   # param: Layer object
    layerRemoved = pyqtSignal(str)                   # param: layerId

    quitRequest = pyqtSignal()

    def __init__(self, settings, webPage, wnd, treeView, parent=None):
        super().__init__(settings, webPage, parent=parent)
        self.wnd = wnd
        self.treeView = treeView

    def abort(self):
        self.abortRequest.emit(True)

    def requestBuildScene(self, properties=None, update_all=True, reload=False):
        self.buildSceneRequest.emit(properties, update_all, reload)

    def requestBuildLayer(self, layer):
        self.buildLayerRequest.emit(layer)

    def requestUpdateWidget(self, name, properties):
        self.updateWidgetRequest.emit(name, properties)

    def requestRunScript(self, string, data=None):
        self.runScriptRequest.emit(string, data)

    def quit(self, controller):
        self.quitRequest.connect(controller.quit)
        self.quitRequest.emit()


class Q3DWindow(QMainWindow):

    def __init__(self, qgisIface, settings, webViewType=WEBVIEWTYPE_WEBENGINE, previewEnabled=True):
        QMainWindow.__init__(self, parent=qgisIface.mainWindow())
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.qgisIface = qgisIface
        self.settings = settings
        self.lastDir = None
        self.loadIcons()

        self.setWindowIcon(QIcon(pluginDir("Qgis2threejs.png")))

        # web view
        if webViewType is not None:
            setCurrentWebView(webViewType)

        ui_wnd.Q3DView = q3dview.Q3DView
        self.ui = Ui_Q3DWindow()
        self.ui.setupUi(self)

        self.webPage = self.ui.webView.page()

        if self.webPage:
            settings.jsonSerializable = self.webPage.isWebEnginePage
            viewName = "WebEngine" if self.webPage.isWebEnginePage else "WebKit"
        else:
            previewEnabled = False
            viewName = ""

        self.iface = Q3DViewerInterface(settings, self.webPage, self, self.ui.treeView, parent=self)
        self.iface.setObjectName("viewerInterface")
        self.iface.statusMessage.connect(self.ui.statusbar.showMessage)
        self.iface.progressUpdated.connect(self.progress)

        self.thread = QThread(self) if RUN_CNTLR_IN_BKGND else None

        self.controller = Q3DController(settings, self.thread)
        self.controller.setObjectName("controller")
        self.controller.enabled = previewEnabled

        if self.thread:
            self.thread.finished.connect(self.controller.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            # start worker thread event loop
            self.thread.start()

        self.controller.connectToIface(self.iface)

        self.setupMenu(self.ui)
        self.setupStatusBar(self.ui, self.iface, previewEnabled, viewName)
        self.ui.treeView.setup(self.iface, self.icons)
        self.ui.treeView.addLayers(settings.layers())

        if self.webPage:
            # to listen messages to be logged
            utils.correspondent = Correspondent(self)
            utils.correspondent.messageSent.connect(self.webPage.logToConsole)

            self.ui.webView.setup(self.iface, settings, wnd=self, enabled=previewEnabled)
            self.ui.webView.fileDropped.connect(self.fileDropped)

            if self.webPage.isWebEnginePage:
                self.ui.webView.devToolsClosed.connect(self.ui.toolButtonConsoleStatus.hide)
        else:
            utils.correspondent = None

            self.ui.webView.disableWidgetsAndMenus(self.ui)

        self.ui.animationPanel.setup(self, settings)

        self.controller.connectToMapCanvas(qgisIface.mapCanvas())

        # restore window geometry and dockwidget layout
        settings = QSettings()
        self.restoreGeometry(settings.value("/Qgis2threejs/wnd/geometry", b""))
        self.restoreState(settings.value("/Qgis2threejs/wnd/state", b""))

        if DEBUG_MODE:
            from .debug_utils import watchGarbageCollection
            watchGarbageCollection(self)

    def closeEvent(self, event):
        self.iface.enabled = False
        self.controller.iface.disconnectFromIface()
        self.controller.disconnectFromMapCanvas()

        if utils.correspondent:
            utils.correspondent.messageSent.disconnect(self.webPage.logToConsole)
            utils.correspondent = None

        if self.webPage and self.webPage.isWebEnginePage:
            self.webPage.jsErrorWarning.disconnect(self.showConsoleStatusIcon)

        # save export settings to a settings file
        try:
            self.settings.setAnimationData(self.ui.animationPanel.data())
            self.settings.saveSettings()
        except Exception as e:
            import traceback
            logMessage(traceback.format_exc(), error=True)

            self.qgisIface.messageBar().pushMessage("Qgis2threejs Error", str(e), level=Qgis.Warning)

        settings = QSettings()
        settings.setValue("/Qgis2threejs/wnd/geometry", self.saveGeometry())
        settings.setValue("/Qgis2threejs/wnd/state", self.saveState())

        # send quit request to the controller and wait until the controller gets ready to quit
        loop = QEventLoop()
        self.controller.iface.readyToQuit.connect(loop.quit)
        self.iface.quit(self.controller)
        loop.exec_()

        # stop worker thread event loop
        if self.thread:
            self.thread.quit()
            self.thread.wait()

        # close dialogs
        for dlg in self.findChildren(QDialog):
            dlg.close()

        # break circular references
        self.iface.wnd = None
        self.ui.treeView.wnd = None
        self.ui.animationPanel.wnd = None
        self.ui.animationPanel.ui.treeWidgetAnimation.wnd = None

        self.ui.webView.teardown()

        QMainWindow.closeEvent(self, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.iface.abort()
        QMainWindow.keyPressEvent(self, event)

    def loadIcons(self):
        self.icons = {
            LayerType.DEM: QgsApplication.getThemeIcon("mIconRaster.svg"),
            LayerType.POINT: QgsApplication.getThemeIcon("mIconPointLayer.svg"),
            LayerType.LINESTRING: QgsApplication.getThemeIcon("mIconLineLayer.svg"),
            LayerType.POLYGON: QgsApplication.getThemeIcon("mIconPolygonLayer.svg"),
            LayerType.POINTCLOUD: QgsApplication.getThemeIcon("mIconPointCloudLayer.svg") if Qgis.QGIS_VERSION_INT >= 31800 else QIcon(pluginDir("svg", "pointcloud.svg"))
        }

    def setupMenu(self, ui):
        ui.menuPanels.addAction(ui.dockWidgetLayers.toggleViewAction())
        ui.menuPanels.addAction(ui.dockWidgetAnimation.toggleViewAction())

        ui.actionGroupCamera = QActionGroup(self)
        ui.actionPerspective.setActionGroup(ui.actionGroupCamera)
        ui.actionOrthographic.setActionGroup(ui.actionGroupCamera)
        ui.actionOrthographic.setChecked(self.settings.isOrthoCamera())
        ui.actionNavigationWidget.setChecked(self.settings.isNavigationEnabled())

        # signal-slot connections
        ui.actionExportToWeb.triggered.connect(self.exportToWeb)

        if WEBENGINE_AVAILABLE or WEBKIT_AVAILABLE:
            ui.actionSaveAsImage.triggered.connect(self.saveAsImage)
            ui.actionSaveAsGLTF.triggered.connect(self.saveAsGLTF)
        else:
            ui.actionSaveAsImage.setEnabled(False)
            ui.actionSaveAsGLTF.setEnabled(False)

        ui.actionLoadSettings.triggered.connect(self.loadSettings)
        ui.actionSaveSettings.triggered.connect(self.saveSettings)
        ui.actionClearSettings.triggered.connect(self.clearSettings)
        ui.actionPluginSettings.triggered.connect(self.pluginSettings)
        ui.actionSceneSettings.triggered.connect(self.showScenePropertiesDialog)
        ui.actionGroupCamera.triggered.connect(self.cameraChanged)
        ui.actionNavigationWidget.toggled.connect(self.iface.navStateChanged)
        ui.actionAddPlane.triggered.connect(self.addPlane)
        ui.actionAddPointCloudLayer.triggered.connect(self.showAddPointCloudLayerDialog)
        ui.actionNorthArrow.triggered.connect(self.showNorthArrowDialog)
        ui.actionHeaderFooterLabel.triggered.connect(self.showHFLabelDialog)
        ui.actionResetCameraPosition.triggered.connect(self.resetCameraState)
        ui.actionReload.triggered.connect(self.reloadPage)
        ui.actionDevTools.triggered.connect(ui.webView.showDevTools)
        ui.actionAlwaysOnTop.toggled.connect(self.alwaysOnTopToggled)
        ui.actionUsage.triggered.connect(self.usage)
        ui.actionHelp.triggered.connect(self.help)
        ui.actionHomePage.triggered.connect(self.homePage)
        ui.actionSendFeedback.triggered.connect(self.sendFeedback)
        ui.actionVersion.triggered.connect(self.about)

        self.alwaysOnTopToggled(False)

        if DEBUG_MODE and self.webPage:
            ui.menuTestDebug = QMenu(ui.menubar)
            ui.menuTestDebug.setTitle("Test&&&Debug")
            ui.menubar.addAction(ui.menuTestDebug.menuAction())

            ui.actionTest = QAction(self)
            ui.actionTest.setText("Run Test")
            ui.menuTestDebug.addAction(ui.actionTest)
            ui.actionTest.triggered.connect(self.runTest)

            if self.webPage.isWebEnginePage:
                ui.actionGPUInfo = QAction(self)
                ui.actionGPUInfo.setText("GPU Info")
                ui.menuTestDebug.addAction(ui.actionGPUInfo)
                ui.actionGPUInfo.triggered.connect(ui.webView.showGPUInfo)

            ui.actionJSInfo = QAction(self)
            ui.actionJSInfo.setText("three.js Info...")
            ui.menuTestDebug.addAction(ui.actionJSInfo)
            ui.actionJSInfo.triggered.connect(ui.webView.showJSInfo)

    def setupStatusBar(self, ui, iface, previewEnabled=True, viewName=""):
        w = ui.progressBar = QProgressBar(ui.statusbar)
        w.setObjectName("progressBar")
        w.setMaximumWidth(250)
        w.setAlignment(Qt.AlignCenter)
        w.hide()
        ui.statusbar.addPermanentWidget(w)

        w = ui.checkBoxPreview = QCheckBox(ui.statusbar)
        w.setObjectName("checkBoxPreview")
        w.setText("Preview" + " ({})".format(viewName) if viewName else "")  # _translate("Q3DWindow", "Preview"))
        w.setChecked(previewEnabled)
        w.toggled.connect(iface.previewStateChanged)
        ui.statusbar.addPermanentWidget(w)

        if self.webPage and self.webPage.isWebEnginePage:
            w = ui.toolButtonConsoleStatus = QToolButton(ui.statusbar)
            w.setObjectName("toolButtonConsoleStatus")
            w.setToolTip("Click this button to open the developer tools.")
            w.hide()
            w.clicked.connect(self.ui.webView.showDevTools)
            ui.statusbar.addPermanentWidget(w)

            self.webPage.loadStarted.connect(ui.toolButtonConsoleStatus.hide)
            self.webPage.jsErrorWarning.connect(self.showConsoleStatusIcon)

    def showConsoleStatusIcon(self, is_error):
        style = QgsApplication.style()
        icon = style.standardIcon(QStyle.SP_MessageBoxCritical if is_error else QStyle.SP_MessageBoxWarning)

        self.ui.toolButtonConsoleStatus.setIcon(icon)
        self.ui.toolButtonConsoleStatus.show()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.windowState() & Qt.WindowMinimized:
                self.runScript("app.pause()")
            else:
                self.runScript("app.resume()")

    def runScript(self, string, data=None, message="", sourceID="Q3DWindow.py", callback=None, wait=False):
        return self.webPage.runScript(string, data, message, sourceID, callback, wait)

    def showStatusMessage(self, msg, timeout_ms=0):
        self.ui.statusbar.showMessage(msg, timeout_ms)

    def progress(self, percentage, msg=None):
        bar = self.ui.progressBar
        if percentage == 100:
            bar.setVisible(False)
            bar.setFormat("")
        else:
            bar.setVisible(True)
            bar.setValue(percentage)
            if msg is not None:
                bar.setFormat(msg)

    # layer tree view
    def showLayerPropertiesDialog(self, layer):
        dialog = PropertiesDialog(self.settings, self.qgisIface, self)
        dialog.propertiesAccepted.connect(self.updateLayerProperties)

        dialog.showLayerProperties(layer)
        return dialog

    # @pyqtSlot(Layer)
    def updateLayerProperties(self, layer):
        orig_layer = self.settings.getLayer(layer.layerId)

        item = self.ui.treeView.itemFromLayerId(layer.layerId)
        if not item:
            return

        if layer.name != orig_layer.name:
            item.setText(layer.name)

        if layer.properties != orig_layer.properties:
            layer.visible = orig_layer.visible      # respect current visible state

            self.iface.requestBuildLayer(layer)

            if layer.properties.get("materials") != orig_layer.properties.get("materials"):
                self.ui.treeView.updateLayerMaterials(item, layer)
                self.ui.animationPanel.tree.materialChanged(layer)

    def getDefaultProperties(self, layer):
        dialog = PropertiesDialog(self.settings, self.qgisIface, self)
        dialog.setLayer(layer)
        return dialog.page.properties()

    def logToConsole(self, message, lineNumber="", sourceID=""):
        if sourceID:
            source = sourceID if lineNumber == "" else "{} ({})".format(sourceID.split("/")[-1], lineNumber)
            text = "{}: {}".format(source, message)
        else:
            text = message

        self.webPage.logToConsole(text)

    def fileDropped(self, urls):
        for url in urls:
            filename = url.fileName()
            if filename in ("cloud.js", "ept.json"):
                self.addPointCloudLayer(url.toString())
            else:
                self.runScript("loadModel('{}')".format(url.toString()))

    # File menu
    def exportToWeb(self):
        from .exportdialog import ExportToWebDialog

        self.settings.setAnimationData(self.ui.animationPanel.data())

        dialog = ExportToWebDialog(self.settings, self.ui.webView.page(), self)
        dialog.show()
        dialog.exec_()

    def saveAsImage(self):
        if not self.ui.checkBoxPreview.isChecked():
            QMessageBox.warning(self, "Save Scene as Image", "You need to enable the preview to use this function.")
            return

        from .imagesavedialog import ImageSaveDialog
        dialog = ImageSaveDialog(self)
        dialog.exec_()

    # @pyqtSlot(int, int, QImage)   # connected to bridge.imageReady signal
    def saveImage(self, width, height, image):
        filename, _ = QFileDialog.getSaveFileName(self, self.tr("Save As"), QDir.homePath(), "PNG files (*.png)")
        if filename:
            image.save(filename)

    def saveAsGLTF(self):
        if not self.ui.checkBoxPreview.isChecked():
            QMessageBox.warning(self, "Save Current Scene as glTF", "You need to enable the preview to use this function.")
            return

        filename, _ = QFileDialog.getSaveFileName(self, self.tr("Save Current Scene as glTF"),
                                                  self.lastDir or QDir.homePath(),
                                                  "glTF files (*.gltf);;Binary glTF files (*.glb)")
        if filename:
            self.ui.statusbar.showMessage("Exporting current scene to a glTF file...")

            self.webPage.loadScriptFile(Script.GLTFEXPORTER)
            self.runScript("saveModelAsGLTF('{0}')".format(filename.replace("\\", "\\\\")))

            self.ui.statusbar.clearMessage()
            self.lastDir = os.path.dirname(filename)

    # @pyqtSlot(bytes, str)     # connected to bridge.modelDataReady signal
    def saveModelData(self, data, filename):
        try:
            with open(filename, "wb") as f:
                f.write(data)

            QMessageBox.information(self, "Save Scene As glTF", "Successfully saved model data: " + filename)

        except Exception as e:
            QMessageBox.warning(self, "Failed to save model data.", str(e))

    def loadSettings(self, filename=None):
        # open file dialog if filename is not specified
        if not filename:
            directory = self.lastDir or QgsProject.instance().homePath() or QDir.homePath()
            filterString = "Settings files (*.qto3settings);;All files (*.*)"
            filename, _ = QFileDialog.getOpenFileName(self, "Load Export Settings", directory, filterString)
            if not filename:
                return

        self.ui.treeView.uncheckAll()       # hide all 3D objects from the scene
        self.ui.treeView.clearLayers()

        settings = self.settings.clone()
        settings.loadSettingsFromFile(filename)

        self.ui.treeView.addLayers(settings.layers())
        self.ui.animationPanel.setData(settings.animationData())

        self.iface.updateExportSettingsRequest.emit(settings)

        self.lastDir = os.path.dirname(filename)

    def saveSettings(self, filename=None):
        # open file dialog if filename is not specified
        if not filename:
            directory = self.lastDir or QgsProject.instance().homePath() or QDir.homePath()
            filename, _ = QFileDialog.getSaveFileName(self, "Save Export Settings", directory, "Settings files (*.qto3settings)")
            if not filename:
                return

            # append .qto3settings extension if filename doesn't have
            if os.path.splitext(filename)[1].lower() != ".qto3settings":
                filename += ".qto3settings"

        self.settings.setAnimationData(self.ui.animationPanel.data())
        self.settings.saveSettings(filename)

        self.lastDir = os.path.dirname(filename)

    def clearSettings(self):
        if QMessageBox.question(self, PLUGIN_NAME, "Are you sure you want to clear export settings?") != QMessageBox.Yes:
            return

        self.ui.treeView.uncheckAll()       # hide all 3D objects from the scene
        self.ui.treeView.clearLayers()
        self.ui.actionPerspective.setChecked(True)

        settings = self.settings.clone()
        settings.clear()
        settings.updateLayers()

        self.ui.treeView.addLayers(settings.layers())
        self.ui.animationPanel.setData({})

        self.iface.updateExportSettingsRequest.emit(settings)

    def pluginSettings(self):
        from .pluginsettings import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec_():
            pluginManager().reloadPlugins()

    # Scene menu
    def showScenePropertiesDialog(self):
        dialog = PropertiesDialog(self.settings, self.qgisIface, self)
        dialog.propertiesAccepted.connect(self.updateSceneProperties)
        dialog.showSceneProperties()
        return dialog

    # @pyqtSlot(dict)
    def updateSceneProperties(self, properties):
        sp = self.settings.sceneProperties()
        if sp == properties:
            return

        w = "radioButton_PtLight"
        isPoint = properties.get(w, False)
        if sp.get(w, False) != isPoint:
            if isPoint:
                sp[w] = isPoint
            else:
                sp.pop(w, 0)

            if sp == properties:
                self.iface.requestRunScript("changeLight('{}')".format("point" if isPoint else "directional"))
                return

        w = "groupBox_Fog"
        reload = bool(sp.get(w) != properties.get(w))
        self.iface.requestBuildScene(properties, reload=reload)

    def addPlane(self):
        layerId = "fp:" + createUid()
        layer = Layer(layerId, "Flat Plane", LayerType.DEM, visible=True)
        layer.properties = self.getDefaultProperties(layer)

        self.iface.layerAdded.emit(layer)
        item = self.ui.treeView.addLayer(layer)
        self.ui.treeView.updateLayerMaterials(item, layer)

    def showAddPointCloudLayerDialog(self):
        dialog = AddPointCloudLayerDialog(self)
        if dialog.exec_():
            url = dialog.ui.lineEdit_Source.text()
            self.addPointCloudLayer(url)

    def addPointCloudLayer(self, url):
        try:
            name = url.split("/")[-2]
        except IndexError:
            name = "No name"

        layerId = "pc:" + name + datetime.now().strftime("%y%m%d%H%M%S")
        properties = {"url": url}

        layer = Layer(layerId, name, LayerType.POINTCLOUD, properties, visible=True)
        self.iface.layerAdded.emit(layer)
        self.ui.treeView.addLayer(layer)

    def reloadPage(self):
        self.webPage.reload()

    # View menu
    def cameraChanged(self, action):
        self.iface.cameraChanged.emit(action == self.ui.actionOrthographic)

    def showNorthArrowDialog(self):
        dialog = NorthArrowDialog(self.settings.widgetProperties("NorthArrow"), self)
        dialog.propertiesAccepted.connect(lambda p: self.iface.requestUpdateWidget("NorthArrow", p))
        dialog.show()
        dialog.exec_()

    def showHFLabelDialog(self):
        dialog = HFLabelDialog(self.settings.widgetProperties("Label"), self)
        dialog.propertiesAccepted.connect(lambda p: self.iface.requestUpdateWidget("Label", p))
        dialog.show()
        dialog.exec_()

    def resetCameraState(self):
        self.webPage.resetCameraState()

    # Window menu
    def alwaysOnTopToggled(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    # Help menu
    def usage(self):
        self.runScript("gui.showInfo()")

    def help(self):
        QDesktopServices.openUrl(QUrl("https://minorua.github.io/Qgis2threejs/docs/"))

    def homePage(self):
        QDesktopServices.openUrl(QUrl("https://github.com/minorua/Qgis2threejs"))

    def sendFeedback(self):
        QDesktopServices.openUrl(QUrl("https://github.com/minorua/Qgis2threejs/issues"))

    def about(self):
        QMessageBox.information(self, PLUGIN_NAME, "Plugin version: {0}".format(PLUGIN_VERSION))

    # Dev menu
    def runTest(self):
        from Qgis2threejs.tests.gui.test_gui import runTest
        runTest(self)


class PropertiesDialog(QDialog):

    propertiesAccepted = pyqtSignal(object)     # dict if scene else Layer

    def __init__(self, settings, qgisIface, parent=None):
        QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.settings = settings
        self.qgisIface = qgisIface
        self.wnd = parent

        self.wheelFilter = WheelEventFilter()

        self.ui = Ui_PropertiesDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.clicked.connect(self.buttonClicked)

        # restore dialog geometry
        settings = QSettings()
        self.restoreGeometry(settings.value("/Qgis2threejs/propdlg/geometry", b""))

    def closeEvent(self, event):
        # save dialog geometry
        settings = QSettings()
        settings.setValue("/Qgis2threejs/propdlg/geometry", self.saveGeometry())
        QDialog.closeEvent(self, event)

    def setLayer(self, layer):
        self.layer = layer.clone()      # create a copy of Layer object
        if self.layer.type == LayerType.DEM:
            self.page = DEMPropertyPage(self, self.layer, self.settings, self.qgisIface.mapCanvas().mapSettings())

        elif self.layer.type == LayerType.POINTCLOUD:
            self.page = PointCloudPropertyPage(self, self.layer)

        else:
            self.page = VectorPropertyPage(self, self.layer, self.settings)

        self.ui.scrollArea.setWidget(self.page)

        # disable wheel event for ComboBox widgets
        for w in self.ui.scrollArea.findChildren(QComboBox):
            w.installEventFilter(self.wheelFilter)

    def buttonClicked(self, button):
        role = self.ui.buttonBox.buttonRole(button)
        if role in [QDialogButtonBox.AcceptRole, QDialogButtonBox.ApplyRole]:
            if isinstance(self.page, ScenePropertyPage):
                self.propertiesAccepted.emit(self.page.properties())
            else:
                nw = self.page.lineEdit_Name
                self.layer.name = nw.text().strip() or nw.placeholderText()
                self.layer.properties = self.page.properties()
                self.propertiesAccepted.emit(self.layer)

                if role == QDialogButtonBox.ApplyRole:
                    self.setLayerDialogTitle(self.layer)

    def showLayerProperties(self, layer):
        self.setLayerDialogTitle(layer)
        self.setLayer(layer)
        self.show()

    def setLayerDialogTitle(self, layer):
        if layer.mapLayer:
            name = layer.mapLayer.name()
            if name != layer.name:
                name = "{} ({})".format(layer.name, name)
        else:
            name = layer.name

        self.setWindowTitle("{} - Layer Properties".format(name))

    def showSceneProperties(self):
        self.setWindowTitle("Scene Settings")
        self.page = ScenePropertyPage(self, self.settings.sceneProperties(), self.qgisIface.mapCanvas())
        self.ui.scrollArea.setWidget(self.page)
        self.show()


class WheelEventFilter(QObject):

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            return True
        return QObject.eventFilter(self, obj, event)


class NorthArrowDialog(QDialog):

    propertiesAccepted = pyqtSignal(dict)

    def __init__(self, properties, parent=None):
        QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        from .ui.northarrowdialog import Ui_NorthArrowDialog
        self.ui = Ui_NorthArrowDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.clicked.connect(self.buttonClicked)

        self.ui.groupBox.setChecked(properties.get("visible", False))
        self.ui.colorButton.setColor(QColor(hex_color(properties.get("color", "#666666"), prefix="#")))

    def buttonClicked(self, button):
        role = self.ui.buttonBox.buttonRole(button)
        if role in [QDialogButtonBox.AcceptRole, QDialogButtonBox.ApplyRole]:
            self.propertiesAccepted.emit({
                "visible": self.ui.groupBox.isChecked(),
                "color": hex_color(self.ui.colorButton.color().name(), prefix="0x")
            })


class HFLabelDialog(QDialog):

    propertiesAccepted = pyqtSignal(dict)

    def __init__(self, properties, parent=None):
        QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        from .ui.hflabeldialog import Ui_HFLabelDialog
        self.ui = Ui_HFLabelDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.clicked.connect(self.buttonClicked)

        self.ui.textEdit_Header.setPlainText(properties.get("Header", ""))
        self.ui.textEdit_Footer.setPlainText(properties.get("Footer", ""))

    def buttonClicked(self, button):
        role = self.ui.buttonBox.buttonRole(button)
        if role in [QDialogButtonBox.AcceptRole, QDialogButtonBox.ApplyRole]:
            self.propertiesAccepted.emit({"Header": self.ui.textEdit_Header.toPlainText(),
                                          "Footer": self.ui.textEdit_Footer.toPlainText()})


class AddPointCloudLayerDialog(QDialog):

    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        from .ui.addpclayerdialog import Ui_AddPointCloudLayerDialog
        self.ui = Ui_AddPointCloudLayerDialog()
        self.ui.setupUi(self)
        self.ui.pushButton_Browse.clicked.connect(self.browseClicked)

    def browseClicked(self):
        url = self.ui.lineEdit_Source.text()
        if url.startswith("file:"):
            directory = QUrl(url).toLocalFile()
        else:
            directory = QDir.homePath()
        filterString = "All supported files (cloud.js ept.json);;Potree format (cloud.js);;Entwine Point Tile format (ept.json)"
        filename, _ = QFileDialog.getOpenFileName(self, "Select a Potree supported file", directory, filterString)
        if filename:
            self.ui.lineEdit_Source.setText(QUrl.fromLocalFile(filename).toString())
