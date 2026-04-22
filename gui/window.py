# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import os
import time
from datetime import datetime

from qgis.PyQt.QtCore import (Qt, QCoreApplication, QDir, QEvent, QEventLoop, QObject, QSettings,
                              QTimer, QUrl, pyqtSignal, pyqtSlot)
from qgis.PyQt.QtGui import QColor, QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (QAction, QActionGroup, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                                 QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                                 QMainWindow, QMenu, QMessageBox, QProgressBar, QPushButton,
                                 QStyle, QToolButton, QVBoxLayout)
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
    modelSaved = pyqtSignal()       # emitted when a glTF export writes its last chunk

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
            ui.actionSaveSceneTest.triggered.connect(self.saveSceneTest)
            ui.actionBuildSettingsFile.triggered.connect(self.build_settings_file)
            ui.actionGenerateTiles.triggered.connect(self.generate_tiles)
        else:
            ui.actionSaveAsImage.setEnabled(False)
            ui.actionSaveAsGLTF.setEnabled(False)
            ui.actionSaveSceneTest.setEnabled(False)
            ui.actionBuildSettingsFile.setEnabled(False)
            ui.actionGenerateTiles.setEnabled(False)

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
            self.controller.taskManager.addReloadPageTask(force_reload=True)

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

        dialog = ExportToWebDialog(self, self.settings, self.controller)
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

    # --- Automate menu -----------------------------------------------------
    # Batch tile export workflow (issue #379):
    #   1. User draws a polygon region in the 3D viewer, which calls
    #      `handlePolygonSelection()` and stashes the coordinates on self.
    #   2. `buildTileSettingsFiles()` divides that region into a tile grid
    #      and writes one .qto3settings file per tile (re-using a template
    #      .qto3settings file that defines layers, materials, DEM/texture
    #      resolution, etc.).
    #   3. `generateTiles()` loads each tile settings file in turn, waits
    #      for the scene to rebuild, and exports the result as a .glb.
    # -----------------------------------------------------------------------

    def handlePolygonSelection(self, coordinates):
        """Receive polygon coordinates drawn in the 3D viewer for batch export."""
        try:
            self.selectedPolygonCoordinates = coordinates
            logger.info(f"Polygon coordinates received: {len(coordinates)} points")
            QMessageBox.information(self, "Polygon Selected",
                                    f"Polygon with {len(coordinates)} points selected. "
                                    "You can now use these coordinates in the Build Settings dialog.")
        except Exception as e:
            logger.error(f"Error handling polygon selection: {e}")
            QMessageBox.warning(self, "Error", f"Error handling polygon selection: {e}")

    def build_settings_file(self):
        """Generate per-tile .qto3settings files from a template and a polygon region."""
        import json

        dialog = BuildSettingsDialog(self, self.qgisIface)
        if not dialog.exec():
            return

        config = dialog.getValues()
        input_file = config["input_file"]
        output_dir = config["output_dir"]
        polygon_coordinates = config["polygon_coordinates"]
        num_tiles_x = config["num_tiles_x"]
        num_tiles_y = config["num_tiles_y"]
        tile_width = config["tile_width"]
        texture_size = config["texture_size"]
        dem_size = config["dem_size"]

        if not polygon_coordinates:
            QMessageBox.warning(self, "Polygon Required",
                                "Please select a polygon in the 3D viewer first, "
                                "then set the polygon boundaries in Build Settings.")
            return

        if not input_file or not output_dir:
            QMessageBox.warning(self, "Input Error",
                                "Input file and output directory must be selected.")
            return

        def is_point_in_polygon(x, y, poly):
            n = len(poly)
            inside = False
            p1x, p1y = poly[0]
            for i in range(n + 1):
                p2x, p2y = poly[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                                if p1x == p2x or x <= xinters:
                                    inside = not inside
                p1x, p1y = p2x, p2y
            return inside

        def do_segments_intersect(p1, p2, p3, p4):
            def ccw(A, B, C):
                return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
            return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

        def tile_intersects_polygon(cx, cy, w, polygon):
            half = w / 2
            corners = [(cx - half, cy - half), (cx + half, cy - half),
                       (cx + half, cy + half), (cx - half, cy + half)]
            for cxy in corners:
                if is_point_in_polygon(cxy[0], cxy[1], polygon):
                    return True
            tx_min, tx_max = cx - half, cx + half
            ty_min, ty_max = cy - half, cy + half
            for p in polygon:
                if tx_min <= p[0] <= tx_max and ty_min <= p[1] <= ty_max:
                    return True
            edges = [(corners[i], corners[(i + 1) % 4]) for i in range(4)]
            for i in range(len(polygon)):
                pe = (polygon[i], polygon[(i + 1) % len(polygon)])
                for te in edges:
                    if do_segments_intersect(te[0], te[1], pe[0], pe[1]):
                        return True
            return False

        try:
            with open(input_file, "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", f"Input file not found: {input_file}")
            return
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", f"Cannot parse JSON in {input_file}.")
            return

        os.makedirs(output_dir, exist_ok=True)

        poly_min_x = min(p[0] for p in polygon_coordinates)
        poly_max_x = max(p[0] for p in polygon_coordinates)
        poly_min_y = min(p[1] for p in polygon_coordinates)
        poly_max_y = max(p[1] for p in polygon_coordinates)

        half_w = tile_width / 2
        start_x = poly_min_x - tile_width
        start_y = poly_min_y - tile_width
        grid_w = int((poly_max_x - poly_min_x + 3 * tile_width) / tile_width) + 2
        grid_h = int((poly_max_y - poly_min_y + 3 * tile_width) / tile_width) + 2
        actual_tiles_x = max(grid_w, num_tiles_x)
        actual_tiles_y = max(grid_h, num_tiles_y)

        tiles_generated = 0
        for row in range(actual_tiles_y):
            for col in range(actual_tiles_x):
                new_x = start_x + col * tile_width + half_w
                new_y = start_y + row * tile_width + half_w

                if (new_x + half_w < poly_min_x or new_x - half_w > poly_max_x or
                        new_y + half_w < poly_min_y or new_y - half_w > poly_max_y):
                    continue

                if not tile_intersects_polygon(new_x, new_y, tile_width, polygon_coordinates):
                    continue

                new_data = json.loads(json.dumps(data))
                new_data["SCENE"]["lineEdit_CenterX"] = str(new_x)
                new_data["SCENE"]["lineEdit_CenterY"] = str(new_y)
                new_data["SCENE"]["lineEdit_Width"] = str(tile_width)
                new_data["SCENE"]["lineEdit_Height"] = str(tile_width)

                for layer in new_data.get("LAYERS", []):
                    if layer.get("geomType") == 0 and "properties" in layer:
                        layer["properties"]["horizontalSlider_DEMSize"] = dem_size
                        for mat in layer["properties"].get("materials", []):
                            mat.setdefault("properties", {})["comboBox_TextureSize"] = str(texture_size)
                        break

                filepath = os.path.join(output_dir, f"tile_{row}_{col}.qto3settings")
                with open(filepath, "w") as out_f:
                    json.dump(new_data, out_f, indent=2)
                tiles_generated += 1

        QMessageBox.information(self, "Tile Settings Generation Complete",
                                f"{tiles_generated} tile settings files generated.\n"
                                f"Output directory: {output_dir}")

    def saveSceneTest(self):
        """Save the current scene as glTF with every DEM material slot included."""
        if not self.ui.checkBoxPreview.isChecked():
            QMessageBox.warning(self, "Save Scene with All Materials",
                                "You need to enable the preview to use this function.")
            return

        filename, _ = QFileDialog.getSaveFileName(self, self.tr("Save Scene with All Materials as glTF"),
                                                  self.lastDir or QDir.homePath(),
                                                  "glTF files (*.gltf);;Binary glTF files (*.glb)")
        if not filename:
            return

        self.ui.statusbar.showMessage("Loading all materials for export...")

        has_dem = False
        for layer in self.settings.layers():
            if layer.visible and layer.type == LayerType.DEM:
                clone = layer.clone()
                clone.opt.allMaterials = True
                self.controller.taskManager.addBuildLayerTask(clone)
                has_dem = True

        if has_dem:
            loop = QEventLoop()

            def checkDone():
                tm = self.controller.taskManager
                if not tm.processingLayer and not tm.taskQueue:
                    loop.quit()

            check_timer = QTimer()
            check_timer.setInterval(200)
            check_timer.timeout.connect(checkDone)

            timeout_timer = QTimer()
            timeout_timer.setSingleShot(True)
            timeout_timer.timeout.connect(loop.quit)
            timeout_timer.start(30000)

            check_timer.start()
            loop.exec()
            check_timer.stop()
            timeout_timer.stop()

        self.ui.statusbar.showMessage("Exporting scene with all materials to glTF...")

        def saveModel():
            self.runScript("saveModelAsGLTF('{}')".format(filename.replace("\\", "\\\\")))
            self.ui.statusbar.clearMessage()

        self.webPage.loadScriptFile(ScriptFile.GLTFEXPORTER, callback=saveModel)
        self.lastDir = os.path.dirname(filename)

    def generate_tiles(self):
        """Batch-export a directory of .qto3settings tile files to glTF (issue #379)."""
        import json as _json

        if not self.ui.checkBoxPreview.isChecked():
            QMessageBox.warning(self, "Generate Tiles",
                                "You need to enable the preview to use this function.")
            return

        settings_dir = QFileDialog.getExistingDirectory(
            self, "Select Directory Containing Tile Settings Files")
        if not settings_dir:
            return

        export_dir = QFileDialog.getExistingDirectory(
            self, "Select Directory to Output Generated Tiles")
        if not export_dir:
            return

        os.makedirs(export_dir, exist_ok=True)

        settings_files = sorted(f for f in os.listdir(settings_dir) if f.endswith(".qto3settings"))
        if not settings_files:
            QMessageBox.warning(self, "No Settings Files",
                                "No .qto3settings files found in the selected directory.")
            return

        logger.info(f"Starting tile generation for {len(settings_files)} files")

        self.setEnabled(False)
        self.ui.statusbar.showMessage("Processing tiles... Please wait.")

        successful = 0
        failed = 0
        failed_files = []

        try:
            for i, settings_file in enumerate(settings_files):
                settings_path = os.path.join(settings_dir, settings_file)
                base_name = os.path.splitext(settings_file)[0]

                has_multi_material = False
                try:
                    with open(settings_path, "r") as f:
                        tile_data = _json.load(f)
                    for ld in tile_data.get("LAYERS", []):
                        if ld.get("geomType") == 0 and \
                                len(ld.get("properties", {}).get("materials", [])) > 1:
                            has_multi_material = True
                            break
                except Exception:
                    pass

                try:
                    self.ui.statusbar.showMessage(
                        f"Processing {i + 1}/{len(settings_files)}: {settings_file}")
                    logger.info(f"Processing tile {i + 1}/{len(settings_files)}: {settings_file}")

                    self.loadSettings(settings_path)

                    # wait for scene rebuild to finish
                    scene_loop = QEventLoop()
                    self.controller.taskManager.allTasksFinalized.connect(scene_loop.quit)
                    scene_timeout = QTimer()
                    scene_timeout.setSingleShot(True)
                    scene_timeout.timeout.connect(scene_loop.quit)
                    scene_timeout.start(60000)
                    scene_loop.exec()
                    scene_timeout.stop()
                    try:
                        self.controller.taskManager.allTasksFinalized.disconnect(scene_loop.quit)
                    except Exception:
                        pass

                    if has_multi_material:
                        self.ui.statusbar.showMessage(
                            f"Loading all materials for {settings_file}...")
                        for layer in self.settings.layers():
                            if layer.visible and layer.type == LayerType.DEM:
                                clone = layer.clone()
                                clone.opt.allMaterials = True
                                self.controller.taskManager.addBuildLayerTask(clone)

                        mtl_loop = QEventLoop()

                        def checkMtlDone():
                            tm = self.controller.taskManager
                            if not tm.processingLayer and not tm.taskQueue:
                                mtl_loop.quit()

                        mtl_check = QTimer()
                        mtl_check.setInterval(200)
                        mtl_check.timeout.connect(checkMtlDone)
                        mtl_timeout = QTimer()
                        mtl_timeout.setSingleShot(True)
                        mtl_timeout.timeout.connect(mtl_loop.quit)
                        mtl_timeout.start(30000)
                        mtl_check.start()
                        mtl_loop.exec()
                        mtl_check.stop()
                        mtl_timeout.stop()

                    gltf_name = base_name + ".glb"
                    filename = os.path.join(export_dir, gltf_name)
                    self.ui.statusbar.showMessage(f"Exporting {settings_file} to glTF...")

                    saved_flag = {"ok": False}

                    def on_model_saved():
                        saved_flag["ok"] = True

                    self.modelSaved.connect(on_model_saved)

                    def do_export():
                        self.runScript("saveModelAsGLTF('{}')".format(
                            filename.replace("\\", "\\\\")))

                    self.webPage.loadScriptFile(ScriptFile.GLTFEXPORTER, callback=do_export)

                    TIMEOUT_SEC = 150
                    POLL_SEC = 0.2
                    elapsed = 0.0
                    while not saved_flag["ok"] and elapsed < TIMEOUT_SEC:
                        QCoreApplication.processEvents()
                        time.sleep(POLL_SEC)
                        elapsed += POLL_SEC

                    try:
                        self.modelSaved.disconnect(on_model_saved)
                    except Exception:
                        pass

                    if saved_flag["ok"] and os.path.exists(filename) and os.path.getsize(filename) > 512:
                        successful += 1
                        logger.info(f"Exported: {gltf_name}")
                    else:
                        raise IOError("Export timed out or file invalid")

                    QCoreApplication.processEvents()

                except Exception as e:
                    logger.error(f"Error processing {settings_file}: {e}")
                    failed += 1
                    failed_files.append(settings_file)
                    continue

        finally:
            self.setEnabled(True)
            self.ui.statusbar.clearMessage()

        total = len(settings_files)
        logger.info(f"Tile generation done - success: {successful}, failed: {failed}")

        msg = (f"Tile Generation Complete!\n\n"
               f"Total: {total}\n"
               f"Successful: {successful}\n"
               f"Failed: {failed}\n"
               f"Success rate: {successful / max(total, 1) * 100:.1f}%")
        if failed_files:
            msg += "\n\nFailed files:\n" + "\n".join(failed_files[:10])
            if len(failed_files) > 10:
                msg += f"\n... and {len(failed_files) - 10} more"

        QMessageBox.information(self, "Tile Generation Complete", msg)

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
                    try:
                        self.modelSaved.emit()
                    except Exception:
                        pass
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


class BuildSettingsDialog(QDialog):
    """Dialog for configuring per-tile settings file generation from a polygon region."""

    def __init__(self, parent=None, qgisIface=None):
        super().__init__(parent)
        self.qgisIface = qgisIface
        self.setWindowTitle("Build Settings File Configuration")
        self._layout = QVBoxLayout(self)

        # Input file
        inputFileGroup = QGroupBox("Input Settings File (template)")
        inputFileLayout = QHBoxLayout()
        self.inputFileEdit = QLineEdit()
        inputFileBtn = QPushButton("Browse...")
        inputFileBtn.clicked.connect(self._selectInputFile)
        inputFileLayout.addWidget(self.inputFileEdit)
        inputFileLayout.addWidget(inputFileBtn)
        inputFileGroup.setLayout(inputFileLayout)
        self._layout.addWidget(inputFileGroup)

        # Output directory
        outputDirGroup = QGroupBox("Output Directory")
        outputDirLayout = QHBoxLayout()
        self.outputDirEdit = QLineEdit()
        outputDirBtn = QPushButton("Browse...")
        outputDirBtn.clicked.connect(self._selectOutputDir)
        outputDirLayout.addWidget(self.outputDirEdit)
        outputDirLayout.addWidget(outputDirBtn)
        outputDirGroup.setLayout(outputDirLayout)
        self._layout.addWidget(outputDirGroup)

        # Polygon region
        polygonGroup = QGroupBox("Polygon Region")
        polygonLayout = QVBoxLayout()
        usePolygonBtn = QPushButton("Use Polygon from 3D Viewer")
        usePolygonBtn.clicked.connect(self._usePolygonFromViewer)
        clearPolygonBtn = QPushButton("Clear Saved Polygon")
        clearPolygonBtn.clicked.connect(self._clearPolygon)
        self.polygonStatusLabel = QLabel(
            "No polygon selected. Select a polygon in the 3D viewer first.")
        self.polygonStatusLabel.setWordWrap(True)
        polygonLayout.addWidget(usePolygonBtn)
        polygonLayout.addWidget(clearPolygonBtn)
        polygonLayout.addWidget(self.polygonStatusLabel)
        polygonGroup.setLayout(polygonLayout)
        self._layout.addWidget(polygonGroup)

        # Tiling settings
        tilingGroup = QGroupBox("Tiling Settings")
        tilingLayout = QFormLayout()
        self.tileWidthEdit = QLineEdit("50")
        tilingLayout.addRow("Tile Width:", self.tileWidthEdit)
        importWidthBtn = QPushButton("Import from Settings File")
        importWidthBtn.clicked.connect(self._importTileWidth)
        tilingLayout.addRow(importWidthBtn)
        self.textureSizeEdit = QLineEdit("2048")
        tilingLayout.addRow("Texture Size:", self.textureSizeEdit)
        importTexBtn = QPushButton("Import from Settings File")
        importTexBtn.clicked.connect(self._importTextureSize)
        tilingLayout.addRow(importTexBtn)
        self.demSizeEdit = QLineEdit("1")
        tilingLayout.addRow("DEM Size:", self.demSizeEdit)
        importDemBtn = QPushButton("Import from Settings File")
        importDemBtn.clicked.connect(self._importDemSize)
        tilingLayout.addRow(importDemBtn)
        self.numTilesXEdit = QLineEdit("200")
        self.numTilesYEdit = QLineEdit("200")
        tilingLayout.addRow("Max Tiles (X):", self.numTilesXEdit)
        tilingLayout.addRow("Max Tiles (Y):", self.numTilesYEdit)
        tilingGroup.setLayout(tilingLayout)
        self._layout.addWidget(tilingGroup)

        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                     QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self._layout.addWidget(buttonBox)

        self._loadPersistedSettings()

    # ---- persistence -----------------------------------------------------
    def _loadPersistedSettings(self):
        import json as _json
        s = QSettings()
        self.inputFileEdit.setText(s.value("/Qgis2threejs/build_settings/inputFile", "", type=str))
        self.outputDirEdit.setText(s.value("/Qgis2threejs/build_settings/outputDir", "", type=str))
        self.tileWidthEdit.setText(s.value("/Qgis2threejs/build_settings/tileWidth", "50", type=str))
        self.textureSizeEdit.setText(s.value("/Qgis2threejs/build_settings/textureSize", "2048", type=str))
        self.demSizeEdit.setText(s.value("/Qgis2threejs/build_settings/demSize", "1", type=str))
        self.numTilesXEdit.setText(s.value("/Qgis2threejs/build_settings/numTilesX", "200", type=str))
        self.numTilesYEdit.setText(s.value("/Qgis2threejs/build_settings/numTilesY", "200", type=str))

        coords_json = s.value("/Qgis2threejs/build_settings/polygonCoordinates", "", type=str)
        if coords_json:
            try:
                coords = _json.loads(coords_json)
                if isinstance(coords, list) and len(coords) >= 3:
                    self.selectedPolygonCoordinates = coords
                    self._updatePolygonLabel(coords)
                    return
            except Exception:
                pass
        self.polygonStatusLabel.setText(
            "No polygon selected. Select a polygon in the 3D viewer first.")

    def _persistSettings(self):
        import json as _json
        s = QSettings()
        s.setValue("/Qgis2threejs/build_settings/inputFile", self.inputFileEdit.text())
        s.setValue("/Qgis2threejs/build_settings/outputDir", self.outputDirEdit.text())
        s.setValue("/Qgis2threejs/build_settings/tileWidth", self.tileWidthEdit.text())
        s.setValue("/Qgis2threejs/build_settings/textureSize", self.textureSizeEdit.text())
        s.setValue("/Qgis2threejs/build_settings/demSize", self.demSizeEdit.text())
        s.setValue("/Qgis2threejs/build_settings/numTilesX", self.numTilesXEdit.text())
        s.setValue("/Qgis2threejs/build_settings/numTilesY", self.numTilesYEdit.text())
        coords = getattr(self, "selectedPolygonCoordinates", None)
        if coords:
            try:
                s.setValue("/Qgis2threejs/build_settings/polygonCoordinates", _json.dumps(coords))
            except Exception:
                pass
        else:
            s.remove("/Qgis2threejs/build_settings/polygonCoordinates")

    def accept(self):
        self._persistSettings()
        super().accept()

    # ---- UI helpers ------------------------------------------------------
    def _updatePolygonLabel(self, coords):
        coord_text = "\n".join(f"Point {i + 1}: ({x:.6f}, {y:.6f})"
                               for i, (x, y) in enumerate(coords))
        self.polygonStatusLabel.setText(
            f"Polygon with {len(coords)} points:\n{coord_text}")

    def _selectInputFile(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Input Settings File", "",
            "Settings files (*.qto3settings);;All files (*.*)")
        if filename:
            self.inputFileEdit.setText(filename)

    def _selectOutputDir(self):
        dirname = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dirname:
            self.outputDirEdit.setText(dirname)

    def _usePolygonFromViewer(self):
        parent_wnd = self.parent()
        coords = getattr(parent_wnd, "selectedPolygonCoordinates", None)
        if coords and len(coords) >= 3:
            self.selectedPolygonCoordinates = coords
            self._updatePolygonLabel(coords)
            self._persistSettings()
            QMessageBox.information(self, "Success",
                                    f"Polygon set with {len(coords)} points from 3D viewer.")
        else:
            QMessageBox.information(
                self, "No Polygon Selected",
                "Please first select a polygon in the 3D viewer:\n"
                "1. Open the 3D viewer\n"
                "2. Draw a polygon by clicking to add points\n"
                "3. Finish selection\n"
                "4. Then click this button again.")

    def _clearPolygon(self):
        if hasattr(self, "selectedPolygonCoordinates"):
            del self.selectedPolygonCoordinates
        self.polygonStatusLabel.setText(
            "No polygon selected. Select a polygon in the 3D viewer first.")
        self._persistSettings()
        QMessageBox.information(self, "Polygon Cleared",
                                "Saved polygon coordinates have been cleared.")

    def _importFromFile(self, extractor, field_edit, field_name):
        import json as _json
        path = self.inputFileEdit.text()
        if not path:
            QMessageBox.warning(self, "No Input File",
                                "Please select an input settings file first.")
            return
        try:
            with open(path, "r") as f:
                data = _json.load(f)
            value = extractor(data)
            if value is not None:
                field_edit.setText(str(value))
            else:
                QMessageBox.information(self, "Not Found",
                                        f"{field_name} not found in the settings file.")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _importTileWidth(self):
        self._importFromFile(
            lambda d: d.get("SCENE", d).get("lineEdit_Width"),
            self.tileWidthEdit, "Tile width")

    def _importTextureSize(self):
        def extractor(d):
            for layer in d.get("LAYERS", []):
                if layer.get("geomType") == 0:
                    mats = layer.get("properties", {}).get("materials", [])
                    if mats:
                        return mats[0].get("properties", {}).get("comboBox_TextureSize")
            return None
        self._importFromFile(extractor, self.textureSizeEdit, "Texture size")

    def _importDemSize(self):
        def extractor(d):
            for layer in d.get("LAYERS", []):
                if layer.get("geomType") == 0:
                    return layer.get("properties", {}).get("horizontalSlider_DEMSize")
            return None
        self._importFromFile(extractor, self.demSizeEdit, "DEM size")

    # ---- result ----------------------------------------------------------
    def getValues(self):
        polygon_coordinates = getattr(self, "selectedPolygonCoordinates", [])
        center_x = center_y = 0.0
        if polygon_coordinates:
            min_x = min(p[0] for p in polygon_coordinates)
            max_x = max(p[0] for p in polygon_coordinates)
            min_y = min(p[1] for p in polygon_coordinates)
            max_y = max(p[1] for p in polygon_coordinates)
            center_x = (min_x + max_x) / 2.0
            center_y = (min_y + max_y) / 2.0

        return {
            "input_file": self.inputFileEdit.text(),
            "output_dir": self.outputDirEdit.text(),
            "polygon_coordinates": polygon_coordinates,
            "num_tiles_x": int(self.numTilesXEdit.text() or 200),
            "num_tiles_y": int(self.numTilesYEdit.text() or 200),
            "center_x": center_x,
            "center_y": center_y,
            "tile_width": float(self.tileWidthEdit.text() or 50),
            "texture_size": int(self.textureSizeEdit.text() or 2048),
            "dem_size": float(self.demSizeEdit.text() or 1),
        }


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
