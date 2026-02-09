# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import os
from datetime import datetime

from qgis.PyQt.QtCore import Qt, QDir, QEvent, QObject, QSettings, QUrl, pyqtSignal, pyqtSlot
from qgis.PyQt.QtGui import QColor, QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (QAction, QActionGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                                 QFileDialog, QMainWindow, QMenu, QMessageBox, QProgressBar, QStyle, QToolButton)
from qgis.core import Qgis, QgsProject, QgsApplication

from . import webview
from .ui import q3dwindow as ui_wnd
from .ui.q3dwindow import Ui_Q3DWindow
from .ui.propertiesdialog import Ui_PropertiesDialog
from .proppages import ScenePropertyPage, DEMPropertyPage, VectorPropertyPage, PointCloudPropertyPage
from .webview import WEBENGINE_AVAILABLE, WEBKIT_AVAILABLE, WEBVIEWTYPE_WEBENGINE, setCurrentWebView
from ..conf import DEBUG_MODE, PLUGIN_NAME, PLUGIN_VERSION, RUN_BLDR_IN_BKGND
from ..core.const import LayerType, ScriptFile
from ..core.controller.controller import Q3DController
from ..core.exportsettings import Layer
from ..core.plugin.pluginmanager import pluginManager
from ..utils import createUid, hex_color, js_bool, logger, openHelp, pluginDir
from ..utils.logging import addLogSignalEmitter, removeLogSignalEmitter


class Q3DWindow(QMainWindow):

    previewEnabledChanged = pyqtSignal(bool)

    def __init__(self, qgisIface, settings, webViewType=WEBVIEWTYPE_WEBENGINE, previewEnabled=True):
        super().__init__(parent=qgisIface.mainWindow())
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.qgisIface = qgisIface
        self.settings = settings        # hold a reference to the original of ExportSettings object
        self.lastDir = None
        self.loadIcons()

        self.setWindowIcon(QIcon(pluginDir("Qgis2threejs.png")))

        # web view
        if webViewType is not None:
            setCurrentWebView(webViewType)

        ui_wnd.Q3DView = webview.Q3DView
        self.ui = Ui_Q3DWindow()
        self.ui.setupUi(self)

        self.webPage = self.ui.webView.page()

        if self.webPage:
            settings.requiresJsonSerializable = self.webPage.isWebEnginePage
            viewName = "WebEngine" if self.webPage.isWebEnginePage else "WebKit"
        else:   # Q3DFallbackView
            previewEnabled = False
            viewName = ""

        self.controller = Q3DController(self, settings, self.webPage, useThread=RUN_BLDR_IN_BKGND, enabledAtStart=previewEnabled)
        self.controller.setObjectName("controller")
        self.controller.statusMessage.connect(self.ui.statusbar.showMessage)
        self.controller.progressUpdated.connect(self.progress)
        self.controller.taskManager.allTasksFinalized.connect(self.hideProgress)

        self._setupMenu(self.ui)
        self._setupStatusBar(self.ui, previewEnabled, viewName)
        self.ui.treeView.setup(self, self.icons, settings.layers())

        if self.webPage:
            self.controller.conn.setup()

            self.webPage.bridge.modelDataReady.connect(self.saveModelData)
            self.webPage.bridge.imageReady.connect(self.saveImage)
            self.webPage.bridge.statusMessage.connect(self.showStatusMessage)

            self.ui.webView.setup(previewEnabled)
            self.ui.webView.fileDropped.connect(self.fileDropped)

            if self.webPage.isWebEnginePage:
                self.ui.webView.devToolsClosed.connect(self.ui.toolButtonConsoleStatus.hide)

            self.previewEnabledChanged.connect(self.setPreviewEnabled)

            addLogSignalEmitter(logger, self.webPage.logToConsole)

        else:   # Q3DFallbackView
            self.ui.webView.disableWidgetsAndMenus(self.ui)

        self.ui.animationPanel.setup(self, settings)

        self.isDirty = False        # flag to indicate whether map canvas extent or project has been changed

        canvas = qgisIface.mapCanvas()
        canvas.renderComplete.connect(self.mapCanvasRendered)
        canvas.extentsChanged.connect(self.setDirty)

        project = QgsProject.instance()
        if hasattr(project, "dirtySet"):     # QGIS 3.20+
            project.dirtySet.connect(self.setDirty)

        # restore window geometry and dockwidget layout
        settings = QSettings()
        self.restoreGeometry(settings.value("/Qgis2threejs/wnd/geometry", b""))
        self.restoreState(settings.value("/Qgis2threejs/wnd/state", b""))

        if DEBUG_MODE:
            from ..utils.debug import setupDestructionLogging
            setupDestructionLogging(self)

        self._modelFile = None
        self._saveModelState = None

    def closeEvent(self, event):
        try:
            self.controller.close()

            # disconnect signals
            self.qgisIface.mapCanvas().renderComplete.disconnect(self.mapCanvasRendered)

            if self.webPage:
                self.controller.conn.teardown()

                removeLogSignalEmitter(logger, self.webPage.logToConsole)

                if self.webPage.isWebEnginePage:
                    self.webPage.jsErrorWarning.disconnect(self.showConsoleStatusIcon)

            # save export settings to a settings file
            self.settings.setAnimationData(self.ui.animationPanel.data())
            self.settings.saveSettings()

            # save window geometry and dockwidget layout
            settings = QSettings()
            settings.setValue("/Qgis2threejs/wnd/geometry", self.saveGeometry())
            settings.setValue("/Qgis2threejs/wnd/state", self.saveState())

            # safely stop worker thread
            self.controller.teardown()

            # close dialogs
            for dlg in self.findChildren(QDialog):
                dlg.close()

            # break circular references
            self.ui.animationPanel.teardown()
            self.ui.treeView.teardown()
            self.ui.webView.teardown()

        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())

            self.qgisIface.messageBar().pushMessage("Qgis2threejs Error", str(e), level=Qgis.Warning)

        QMainWindow.closeEvent(self, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.controller.abort()
        QMainWindow.keyPressEvent(self, event)

    def loadIcons(self):
        self.icons = {
            LayerType.DEM: QgsApplication.getThemeIcon("mIconRaster.svg"),
            LayerType.POINT: QgsApplication.getThemeIcon("mIconPointLayer.svg"),
            LayerType.LINESTRING: QgsApplication.getThemeIcon("mIconLineLayer.svg"),
            LayerType.POLYGON: QgsApplication.getThemeIcon("mIconPolygonLayer.svg"),
            LayerType.POINTCLOUD: QgsApplication.getThemeIcon("mIconPointCloudLayer.svg") if Qgis.QGIS_VERSION_INT >= 31800 else QIcon(pluginDir("svg", "pointcloud.svg"))
        }

    def _setupMenu(self, ui):
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
        ui.actionNavigationWidget.toggled.connect(self.navStateChanged)
        ui.actionAddPlane.triggered.connect(self.addPlane)
        ui.actionAddPointCloudLayer.triggered.connect(self.showAddPointCloudLayerDialog)
        ui.actionNorthArrow.triggered.connect(self.showNorthArrowDialog)
        ui.actionHeaderFooterLabel.triggered.connect(self.showHFLabelDialog)
        if self.webPage:
            ui.actionResetCameraPosition.triggered.connect(self.controller.resetCameraState)
            ui.actionReload.triggered.connect(self.reloadPage)
            ui.actionDevTools.triggered.connect(ui.webView.showDevTools)
        ui.actionAlwaysOnTop.toggled.connect(self.alwaysOnTopToggled)
        ui.actionUsage.triggered.connect(self.usage)
        ui.actionHelp.triggered.connect(openHelp)
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

    def _setupStatusBar(self, ui, previewEnabled=True, viewName=""):
        w = ui.progressBar = QProgressBar(ui.statusbar)
        w.setObjectName("progressBar")
        w.setMaximumWidth(250)
        w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w.hide()
        ui.statusbar.addPermanentWidget(w)

        w = ui.checkBoxPreview = QCheckBox(ui.statusbar)
        w.setObjectName("checkBoxPreview")
        w.setText("Preview" + (f" ({viewName})" if viewName else ""))  # _translate("Q3DWindow", "Preview"))
        w.setChecked(previewEnabled)
        w.toggled.connect(self.previewEnabledChanged)
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
        if self.ui.toolButtonConsoleStatus.isVisible() and not is_error:
            # do not replace error icon with warning icon
            return

        if is_error:
            icon = QgsApplication.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
        else:
            if os.name == "nt":
                icon = QgsApplication.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
            else:
                icon = QgsApplication.getThemeIcon("mIconWarning.svg")

        self.ui.toolButtonConsoleStatus.setIcon(icon)
        self.ui.toolButtonConsoleStatus.show()

    def setPreviewEnabled(self, enabled):
        self.controller.enabled = enabled

        self.runScript("setPreviewEnabled({})".format(js_bool(enabled)))

        if enabled:
            self.controller.taskManager.addBuildSceneTask()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.runScript("app.pause()")
            else:
                self.runScript("app.resume()")

    def runScript(self, string, message="", sourceID="Q3DWindow.py", callback=None, wait=False):
        return self.webPage.runScript(string, message, sourceID, callback, wait)

    def showStatusMessage(self, msg, timeout_ms=0):
        self.ui.statusbar.showMessage(msg, timeout_ms)

    @pyqtSlot(int, int, str)
    def progress(self, current=0, total=100, msg=""):
        self.ui.progressBar.show()
        self.ui.progressBar.setValue(int(current / total * 100))
        if msg:
            self.ui.progressBar.setFormat(msg)

    @pyqtSlot()
    def hideProgress(self):
        self.ui.progressBar.hide()
        self.ui.progressBar.setFormat("")

    # map canvas and project events
    @pyqtSlot()
    def mapCanvasRendered(self):
        if self.isDirty:
            self.settings.setMapSettings(self.qgisIface.mapCanvas().mapSettings())
            self.controller.taskManager.addBuildSceneTask()
            self.isDirty = False

    @pyqtSlot()
    def setDirty(self):
        self.isDirty = True

    # layer tree view
    def showLayerPropertiesDialog(self, layer, tab=0):
        dialog = PropertiesDialog(self, self.settings, self.qgisIface)
        dialog.propertiesAccepted.connect(self.updateLayerProperties)

        dialog.showLayerProperties(layer, tab)
        return dialog

    # @pyqtSlot(Layer)
    def updateLayerProperties(self, layer):
        orig_layer = self.settings.getLayer(layer.layerId).clone()

        self.settings.setLayer(layer)

        item = self.ui.treeView.itemFromLayerId(layer.layerId)
        if not item:
            logger.warning(f"Tree item for layer '{layer.layerId}' not found.")
            return

        if layer.name != orig_layer.name:
            item.setText(layer.name)

        if layer.properties != orig_layer.properties:
            layer.visible = orig_layer.visible      # respect current visible state

            self.controller.taskManager.addBuildLayerTask(layer)

            if layer.properties.get("materials") != orig_layer.properties.get("materials"):
                self.ui.treeView.updateLayerMaterials(item, layer)
                self.ui.animationPanel.tree.materialChanged(layer)

    def getDefaultProperties(self, layer):
        dialog = PropertiesDialog(self, self.settings, self.qgisIface)
        dialog.setLayer(layer)
        return dialog.page.properties()

    def fileDropped(self, urls):
        for url in urls:
            filename = url.fileName()
            if filename in ("cloud.js", "ept.json"):
                self.addPointCloudLayer(url.toString())
            else:
                self.runScript(f"loadModel('{url.toString()}')")

    # File menu
    def exportToWeb(self):
        from .exportdialog import ExportToWebDialog

        self.settings.setAnimationData(self.ui.animationPanel.data())

        dialog = ExportToWebDialog(self, self.settings, self.ui.webView.page())
        dialog.show()
        dialog.exec()

    def saveAsImage(self):
        if not self.ui.checkBoxPreview.isChecked():
            QMessageBox.warning(self, "Save Scene as Image", "You need to enable the preview to use this function.")
            return

        from .imagesavedialog import ImageSaveDialog
        dialog = ImageSaveDialog(self)
        dialog.exec()

    # @pyqtSlot(QImage, str, bool)   # connected from bridge.imageReady signal
    def saveImage(self, image, copy_to_clipboard=False):
        if copy_to_clipboard:
            QgsApplication.clipboard().setImage(image)
            self.ui.statusbar.showMessage("Image has been rendered and copied to clipboard.", 5000)
            return

        filename, _ = QFileDialog.getSaveFileName(self, self.tr("Save As"), QDir.homePath(), "PNG files (*.png)")
        if filename:
            if not filename.lower().endswith(".png"):       # fix for #278
                filename += ".png"

            image.save(filename)
            self.ui.statusbar.showMessage("Image has been saved to file.", 5000)

    def saveAsGLTF(self):
        if not self.ui.checkBoxPreview.isChecked():
            QMessageBox.warning(self, "Save Current Scene as glTF", "You need to enable the preview to use this function.")
            return

        filename, _ = QFileDialog.getSaveFileName(self, self.tr("Save Current Scene as glTF"),
                                                  self.lastDir or QDir.homePath(),
                                                  "glTF files (*.gltf);;Binary glTF files (*.glb)")
        if not filename:
            return

        def saveModel():
            self.runScript("saveModelAsGLTF('{}')".format(filename.replace("\\", "\\\\")))
            self.ui.statusbar.clearMessage()

        _, ext = os.path.splitext(filename)
        self.ui.statusbar.showMessage(f"Exporting current scene to a {ext} file...")
        self.webPage.loadScriptFile(ScriptFile.GLTFEXPORTER, callback=saveModel)

        self.lastDir = os.path.dirname(filename)

    # @pyqtSlot(bytes, str, bool, bool)     # connected to bridge.modelDataReady signal
    def saveModelData(self, data, filename, is_first, is_last):
        SAVING = 1
        ERR = 2

        try:
            if is_first:
                if self._modelFile:
                    self._modelFile.close()

                self._modelFile = open(filename, "wb")
                self._saveModelState = SAVING

            self._modelFile.write(data)

            if is_last:
                self._modelFile.close()
                self._modelFile = None

                if self._saveModelState == SAVING:
                    QMessageBox.information(self, "Save Scene As glTF", "Successfully saved model data: " + filename)
                self._saveModelState = None
                return

        except Exception as e:
            if self._saveModelState != ERR:
                QMessageBox.critical(self, "Failed to save model data.", str(e))
            self._saveModelState = ERR

    def loadSettings(self, filename=None):
        # open file dialog if filename is not specified
        if not filename:
            directory = self.lastDir or QgsProject.instance().homePath() or QDir.homePath()
            filterString = "Settings files (*.qto3settings);;All files (*.*)"
            filename, _ = QFileDialog.getOpenFileName(self, "Load Export Settings", directory, filterString)
            if not filename:
                return

        self.lastDir = os.path.dirname(filename)

        self.ui.treeView.uncheckAll()       # hide all 3D objects from the scene
        self.ui.treeView.clearLayers()

        self.settings.initialize(mapSettings=self.qgisIface.mapCanvas().mapSettings(),
                                 isPreview=True,
                                 requiresJsonSerializable=self.webPage.isWebEnginePage if self.webPage else False)
        self.settings.loadSettingsFromFile(filename)

        self.ui.treeView.addLayers(self.settings.layers())
        self.ui.animationPanel.setData(self.settings.animationData())

        self.controller.taskManager.addReloadPageTask()

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
        if QMessageBox.question(self, PLUGIN_NAME, "Are you sure you want to clear export settings?") != QMessageBox.StandardButton.Yes:
            return

        self.ui.treeView.uncheckAll()       # hide all 3D objects from the scene
        self.ui.treeView.clearLayers()
        self.ui.actionPerspective.setChecked(True)

        self.settings.initialize(mapSettings=self.qgisIface.mapCanvas().mapSettings(),
                                 isPreview=True,
                                 requiresJsonSerializable=self.webPage.isWebEnginePage if self.webPage else False)
        self.settings.updateLayers()

        self.ui.treeView.addLayers(self.settings.layers())
        self.ui.animationPanel.setData({})

        self.controller.taskManager.addReloadPageTask()

    def pluginSettings(self):
        from .pluginsettings import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec():
            pluginManager().reloadPlugins()

    # Scene menu
    def showScenePropertiesDialog(self):
        dialog = PropertiesDialog(self, self.settings, self.qgisIface)
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
                self.runScript("changeLight('{}')".format("point" if isPoint else "directional"))
                return

        w = "groupBox_Fog"
        reload = bool(sp.get(w) != properties.get(w))

        self.settings.setSceneProperties(properties)
        if reload:
            self.controller.taskManager.addReloadPageTask()
        else:
            self.controller.taskManager.addBuildSceneTask()

    def addPlane(self):
        layerId = "fp:" + createUid()
        layer = Layer(layerId, "Flat Plane", LayerType.DEM)
        layer.properties = self.getDefaultProperties(layer)

        self.settings.addLayer(layer)
        self.controller.taskManager.addBuildLayerTask(layer)

        item = self.ui.treeView.addLayer(layer)
        self.ui.treeView.updateLayerMaterials(item, layer)

    def showAddPointCloudLayerDialog(self):
        dialog = AddPointCloudLayerDialog(self)
        if dialog.exec():
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

        self.settings.addLayer(layer)
        self.controller.taskManager.addBuildLayerTask(layer)

        self.ui.treeView.addLayer(layer)

    # View menu
    def cameraChanged(self, action):
        is_ortho = bool(action == self.ui.actionOrthographic)

        self.settings.setCamera(is_ortho)
        self.runScript(f"switchCamera({js_bool(is_ortho)})")

    def navStateChanged(self, enabled):
        self.settings.setNavigationEnabled(enabled)
        self.runScript(f"setNavigationEnabled({js_bool(enabled)})")

    def showNorthArrowDialog(self):
        dialog = NorthArrowDialog(self, self.settings.widgetProperties("NorthArrow"))
        dialog.propertiesAccepted.connect(lambda p: self.updateWidgetProperties("NorthArrow", p))
        dialog.show()
        dialog.exec()

    def showHFLabelDialog(self):
        dialog = HFLabelDialog(self, self.settings.widgetProperties("Label"))
        dialog.propertiesAccepted.connect(lambda p: self.updateWidgetProperties("Label", p))
        dialog.show()
        dialog.exec()

    def updateWidgetProperties(self, name, properties):
        self.settings.setWidgetProperties(name, properties)
        self.controller.updateWidget(name, properties)

    def reloadPage(self):
        self.controller.abort()
        self.controller.taskManager.addReloadPageTask(force_reload=True)

    # Window menu
    def alwaysOnTopToggled(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    # Help menu
    def usage(self):
        self.runScript("gui.showInfo()")

    def homePage(self):
        QDesktopServices.openUrl(QUrl("https://github.com/minorua/Qgis2threejs"))

    def sendFeedback(self):
        QDesktopServices.openUrl(QUrl("https://github.com/minorua/Qgis2threejs/issues"))

    def about(self):
        QMessageBox.information(self, PLUGIN_NAME, "Plugin version: {0}".format(PLUGIN_VERSION))

    # Dev menu
    def runTest(self):
        from ..tests.gui.test_gui import runTest
        runTest(self)


class PropertiesDialog(QDialog):

    propertiesAccepted = pyqtSignal(object)     # dict if scene else Layer

    def __init__(self, parent, settings, qgisIface):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

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
        try:
            # save dialog geometry
            settings = QSettings()
            settings.setValue("/Qgis2threejs/propdlg/geometry", self.saveGeometry())
        except:
            pass

        QDialog.closeEvent(self, event)

    def setLayer(self, layer):
        self.layer = layer.clone()      # create a copy of Layer object
        if self.layer.type == LayerType.DEM:
            self.page = DEMPropertyPage(self, self.layer, self.settings, self.qgisIface.mapCanvas().mapSettings())

        elif self.layer.type == LayerType.POINTCLOUD:
            self.page = PointCloudPropertyPage(self, self.layer)

        else:
            self.page = VectorPropertyPage(self, self.layer, self.settings)

        self.ui.verticalLayout.insertWidget(0, self.page)

        # disable wheel event for ComboBox widgets
        for w in self.page.findChildren(QComboBox):
            w.installEventFilter(self.wheelFilter)

    def buttonClicked(self, button):
        role = self.ui.buttonBox.buttonRole(button)
        if role in [QDialogButtonBox.ButtonRole.AcceptRole, QDialogButtonBox.ButtonRole.ApplyRole]:
            if isinstance(self.page, ScenePropertyPage):
                self.propertiesAccepted.emit(self.page.properties())
            else:
                nw = self.page.lineEdit_Name
                self.layer.name = nw.text().strip() or nw.placeholderText()
                self.layer.properties = self.page.properties()
                self.propertiesAccepted.emit(self.layer)

                if role == QDialogButtonBox.ButtonRole.ApplyRole:
                    self.setLayerDialogTitle(self.layer)

        elif role == QDialogButtonBox.ButtonRole.HelpRole:
            pageName = type(self.page).__name__.replace("PropertyPage", "").lower()
            tab = self.page.tabWidget.currentIndex() if hasattr(self.page, "tabWidget") else ""
            openHelp(f"dlg={pageName}&tab={tab}")

    def showLayerProperties(self, layer, tab=0):
        self.setLayerDialogTitle(layer)
        self.setLayer(layer)
        if tab and hasattr(self.page, "tabWidget"):
            self.page.tabWidget.setCurrentIndex(tab)

        self.show()

    def setLayerDialogTitle(self, layer):
        if layer.mapLayer:
            name = layer.mapLayer.name()
            if name != layer.name:
                name = f"{layer.name} ({name})"
        else:
            name = layer.name

        self.setWindowTitle("{} - Layer Properties".format(name))

    def showSceneProperties(self):
        self.setWindowTitle("Scene Settings")
        self.page = ScenePropertyPage(self, self.settings.sceneProperties(), self.qgisIface.mapCanvas())
        self.ui.verticalLayout.insertWidget(0, self.page)
        self.show()


class WheelEventFilter(QObject):

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            return True
        return QObject.eventFilter(self, obj, event)


class NorthArrowDialog(QDialog):

    propertiesAccepted = pyqtSignal(dict)

    def __init__(self, parent, properties):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        from .ui.northarrowdialog import Ui_NorthArrowDialog
        self.ui = Ui_NorthArrowDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.clicked.connect(self.buttonClicked)

        self.ui.groupBox.setChecked(properties.get("visible", False))
        self.ui.colorButton.setColor(QColor(hex_color(properties.get("color", "#666666"), prefix="#")))

    def buttonClicked(self, button):
        role = self.ui.buttonBox.buttonRole(button)
        if role in [QDialogButtonBox.ButtonRole.AcceptRole, QDialogButtonBox.ButtonRole.ApplyRole]:
            self.propertiesAccepted.emit({
                "visible": self.ui.groupBox.isChecked(),
                "color": hex_color(self.ui.colorButton.color().name(), prefix="0x")
            })
        elif role == QDialogButtonBox.ButtonRole.HelpRole:
            openHelp("dlg=northarrow")


class HFLabelDialog(QDialog):

    propertiesAccepted = pyqtSignal(dict)

    def __init__(self, parent, properties):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        from .ui.hflabeldialog import Ui_HFLabelDialog
        self.ui = Ui_HFLabelDialog()
        self.ui.setupUi(self)
        self.ui.buttonBox.clicked.connect(self.buttonClicked)

        self.ui.textEdit_Header.setPlainText(properties.get("Header", ""))
        self.ui.textEdit_Footer.setPlainText(properties.get("Footer", ""))

    def buttonClicked(self, button):
        role = self.ui.buttonBox.buttonRole(button)
        if role in [QDialogButtonBox.ButtonRole.AcceptRole, QDialogButtonBox.ButtonRole.ApplyRole]:
            self.propertiesAccepted.emit({"Header": self.ui.textEdit_Header.toPlainText(),
                                          "Footer": self.ui.textEdit_Footer.toPlainText()})
        elif role == QDialogButtonBox.ButtonRole.HelpRole:
            openHelp("dlg=hflabel")


class AddPointCloudLayerDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)

        from .ui.addpclayerdialog import Ui_AddPointCloudLayerDialog
        self.ui = Ui_AddPointCloudLayerDialog()
        self.ui.setupUi(self)
        self.ui.pushButton_Browse.clicked.connect(self.browseClicked)
        self.ui.buttonBox.helpRequested.connect(self.helpClicked)

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

    def helpClicked(self):
        openHelp("dlg=addpc")
