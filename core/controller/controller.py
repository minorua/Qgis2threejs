# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import time
from qgis.PyQt.QtCore import QObject, QTimer, QThread, pyqtSignal, pyqtSlot
from qgis.core import QgsApplication

from ..build.builder import ThreeJSBuilder
from ..const import LayerType, ScriptFile
from ..exportsettings import ExportSettings, Layer
from ...conf import DEBUG_MODE, RUN_BLDR_IN_BKGND
from ...utils import hex_color, js_bool, logger


class Q3DControllerInterface(QObject):

    # signals - controller iface to builder
    buildSceneRequest = pyqtSignal()
    buildLayerRequest = pyqtSignal(object)       # Layer

    # signals - controller iface to viewer iface
    dataSent = pyqtSignal(dict)                  # data
    scriptSent = pyqtSignal(str, object, str)    # script, data, msg_shown_in_log_panel
    statusMessage = pyqtSignal(str, int)         # message, timeout_ms
    progressUpdated = pyqtSignal(int, str)       # percentage, msg
    loadScriptsRequest = pyqtSignal(list, bool)  # list of script ID, force (if False, do not load a script that is already loaded)
    readyToQuit = pyqtSignal()

    def __init__(self, controller=None):
        super().__init__(parent=controller)

        self.controller = controller
        self.builder = None
        self.viewIface = None

    def teardown(self):
        self.disconnectFromBuilder()
        self.disconnectFromIface()
        self.controller = None

    # controller interface <-> builder
    def connectToBuilder(self, builder):
        self.builder = builder

        self.buildSceneRequest.connect(builder.buildSceneSlot)
        self.buildLayerRequest.connect(builder.buildLayerSlot)

        builder.dataReady.connect(self.dataSent)

        if self.controller:
            builder.taskCompleted.connect(self.controller.taskCompleted)

    def disconnectFromBuilder(self):
        builder = self.builder

        self.buildSceneRequest.disconnect(builder.buildSceneSlot)
        self.buildLayerRequest.disconnect(builder.buildLayerSlot)

        builder.dataReady.disconnect(self.dataSent)

        if self.controller:
            builder.taskCompleted.disconnect(self.controller.taskCompleted)

        self.builder = None

    def requestBuildScene(self):
        self.buildSceneRequest.emit()

    def requestBuildLayer(self, layer):
        self.buildLayerRequest.emit(layer)

    # controller interface <-> viewer interface
    def connectToIface(self, iface):
        """iface: web view side interface (Q3DInterface or its subclass)"""
        self.viewIface = iface

        self.dataSent.connect(iface.sendJSONObject)
        self.scriptSent.connect(iface.runScript)
        self.loadScriptsRequest.connect(iface.loadScriptFiles)
        self.statusMessage.connect(iface.statusMessage)
        self.progressUpdated.connect(iface.progressUpdated)

        if hasattr(iface, "abortRequest"):
            iface.abortRequest.connect(self.controller.abort)
            iface.buildSceneRequest.connect(self.controller.addBuildSceneTask)
            iface.buildLayerRequest.connect(self.controller.addBuildLayerTask)
            iface.updateWidgetRequest.connect(self.controller.requestUpdateWidget)
            iface.runScriptRequest.connect(self.controller.addRunScriptTask)

            iface.updateExportSettingsRequest.connect(self.controller.updateExportSettings)
            iface.cameraChanged.connect(self.controller.switchCamera)
            iface.navStateChanged.connect(self.controller.setNavigationEnabled)
            iface.previewStateChanged.connect(self.controller.setPreviewEnabled)
            iface.layerAdded.connect(self.controller.addLayer)
            iface.layerRemoved.connect(self.controller.removeLayer)

    def disconnectFromIface(self):
        iface = self.viewIface

        self.dataSent.disconnect(iface.sendJSONObject)
        self.scriptSent.disconnect(iface.runScript)
        self.loadScriptsRequest.disconnect(iface.loadScriptFiles)
        self.statusMessage.disconnect(iface.statusMessage)
        self.progressUpdated.disconnect(iface.progressUpdated)

        if hasattr(iface, "abortRequest"):
            iface.abortRequest.disconnect(self.controller.abort)
            iface.buildSceneRequest.disconnect(self.controller.addBuildSceneTask)
            iface.buildLayerRequest.disconnect(self.controller.addBuildLayerTask)
            iface.updateWidgetRequest.disconnect(self.controller.requestUpdateWidget)
            iface.runScriptRequest.disconnect(self.controller.addRunScriptTask)

            iface.updateExportSettingsRequest.disconnect(self.controller.updateExportSettings)
            iface.cameraChanged.disconnect(self.controller.switchCamera)
            iface.navStateChanged.disconnect(self.controller.setNavigationEnabled)
            iface.previewStateChanged.disconnect(self.controller.setPreviewEnabled)
            iface.layerAdded.disconnect(self.controller.addLayer)
            iface.layerRemoved.disconnect(self.controller.removeLayer)

        self.viewIface = None

    def sendJSONObject(self, obj):
        self.dataSent.emit(obj)

    def runScript(self, string, data=None, msg=""):
        self.scriptSent.emit(string, data, msg)

    def showStatusMessage(self, msg, timeout_ms=0):
        """show message in status bar"""
        self.statusMessage.emit(msg, timeout_ms)

    def clearStatusMessage(self):
        """clear message in status bar"""
        self.statusMessage.emit("", 0)

    def showMessageBar(self, msg, timeout_ms=0, warning=False):
        """show message bar at top of web view"""
        self.runScript("showMessageBar(pyData(), {}, {})".format(timeout_ms, js_bool(warning)), data=msg)

    def progress(self, percentage=100, msg=""):
        self.progressUpdated.emit(int(percentage), msg)

    def loadScriptFile(self, scriptFileId, force=False):
        self.loadScriptsRequest.emit([scriptFileId], force)

    def loadScriptFiles(self, ids, force=False):
        self.loadScriptsRequest.emit(ids, force)


class Q3DController(QObject):

    # requests
    BUILD_SCENE_ALL = 1     # build scene
    BUILD_SCENE = 2         # build scene, but do not update scene options such asbackground color, coordinates display mode and so on
    UPDATE_SCENE_OPTS = 3   # update scene options
    RELOAD_PAGE = 4

    def __init__(self, settings=None, webPage=None, parent=None):
        super().__init__(parent)

        if settings is None:
            defaultSettings = {}
            settings = ExportSettings()
            settings.loadSettings(defaultSettings)

            err_msg = settings.checkValidity()
            if err_msg:
                logger.warning("Invalid settings: " + err_msg)

        self.settings = settings
        self.builder = ThreeJSBuilder(settings, parent=self)

        self.thread = None
        if webPage and RUN_BLDR_IN_BKGND:
            self.thread = QThread(self)

            # move builder to worker thread
            self.builder.moveToThread(self.thread)

            self.thread.finished.connect(self.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)

            # start worker thread event loop
            self.thread.start()

        self.iface = Q3DControllerInterface(self)
        self.iface.setObjectName("controllerInterface")
        self.iface.connectToBuilder(self.builder)

        self.enabled = True
        self.aborted = False  # layer export aborted
        self.processingLayer = None
        self.mapCanvas = None

        self.requestQueue = []
        self.timer = QTimer(self)
        self.timer.setInterval(1)
        self.timer.setSingleShot(True)

        self.timer.timeout.connect(self._processRequests)

        # delegating methods
        self.connectToIface = self.iface.connectToIface
        self.disconnectFromIface = self.iface.disconnectFromIface

    def teardown(self):
        self.timer.stop()
        self.timer.timeout.disconnect(self._processRequests)

        self.iface.teardown()

    # @pyqtSlot(QPainter)
    def _requestBuildScene(self, _=None):
        self.addBuildSceneTask(update_all=False)

    def buildScene(self):
        if self.processingLayer:
            logger.info("Previous processing is still in progress. Cannot start to build scene.")
            return False

        self.aborted = False

        self.iface.progress(0, "Building scene")
        self.iface.requestBuildScene()

    def updateSceneOptions(self):
        sp = self.settings.sceneProperties()

        # outline effect
        self.iface.runScript("setOutlineEffectEnabled({})".format(js_bool(sp.get("checkBox_Outline"))))

        # update background color
        params = "{0}, 1".format(hex_color(sp.get("colorButton_Color", 0), prefix="0x")) if sp.get("radioButton_Color") else "0, 0"
        self.iface.runScript("setBackgroundColor({0})".format(params))

        # coordinate display
        self.iface.runScript("Q3D.Config.coord.visible = {};".format(js_bool(self.settings.coordDisplay())))

        latlon = self.settings.isCoordLatLon()
        self.iface.runScript("Q3D.Config.coord.latlon = {};".format(js_bool(latlon)))
        if latlon:
            self.iface.loadScriptFile(ScriptFile.PROJ4)

    def buildLayer(self, layer):
        self.aborted = False
        if isinstance(layer, dict):
            layer = Layer.fromDict(layer)

        if self.processingLayer:
            logger.info('Previous processing is still in progress. Cannot start to build layer "{}".'.format(layer.name))
            return False

        self._buildLayer(layer)

        if len(self.settings.layersToExport()) == 1:
            self.addRunScriptTask("adjustCameraPos()")

    def _buildLayer(self, layer):
        self.processingLayer = layer

        pmsg = "Building {0}...".format(layer.name)
        self.iface.progress(0, pmsg)

        if layer.type == LayerType.POINT and layer.properties.get("comboBox_ObjectType") == "3D Model":
            self.iface.loadScriptFiles([ScriptFile.COLLADALOADER,
                                        ScriptFile.GLTFLOADER])

        elif layer.type == LayerType.LINESTRING and layer.properties.get("comboBox_ObjectType") == "Thick Line":
            self.iface.loadScriptFiles([ScriptFile.MESHLINE])

        elif layer.type == LayerType.POINTCLOUD:
            self.iface.loadScriptFiles([ScriptFile.FETCH,
                                        ScriptFile.POTREE,
                                        ScriptFile.PCLAYER])

        self.iface.requestBuildLayer(layer)

    def hideLayer(self, layer):
        """hide layer and remove all objects from the layer"""
        self.iface.runScript('hideLayer("{}", true)'.format(layer.jsLayerId))

    def hideAllLayers(self):
        """hide all layers and remove all objects from the layers"""
        self.iface.runScript("hideAllLayers(true)")

    def taskCompleted(self):
        self.processingLayer = None

        self.iface.progress()
        self.iface.clearStatusMessage()

        self._processRequests()

    def processRequests(self):
        self.timer.stop()
        if self.requestQueue:
            self.timer.start()

    def _processRequests(self):
        if not self.enabled or self.processingLayer or not self.requestQueue:
            return

        try:
            if self.RELOAD_PAGE in self.requestQueue:
                self.requestQueue.clear()
                self.iface.runScript("location.reload()")

            elif self.BUILD_SCENE_ALL in self.requestQueue:
                self.requestQueue.clear()
                self.requestQueue.append(self.UPDATE_SCENE_OPTS)
                self._addVisibleLayersToQueue()

                self.buildScene()

            elif self.BUILD_SCENE in self.requestQueue:
                self.requestQueue.clear()
                self._addVisibleLayersToQueue()

                self.buildScene()

            else:
                item = self.requestQueue.pop(0)
                if isinstance(item, Layer):
                    # TODO: check if the map layer still exists
                    if item.visible:
                        self.buildLayer(item)
                    else:
                        self.hideLayer(item)

                elif isinstance(item, dict):
                    self.iface.runScript(item.get("string"), item.get("data"))

                elif item == self.UPDATE_SCENE_OPTS:
                    self.updateSceneOptions()

                else:
                    logger.warning(f"Unknown request: {item}")

        except Exception as e:
            import traceback
            logger.warning(traceback.format_exc())

            self.iface.showMessageBar("One or more errors occurred. See log messages panel in QGIS main window for details.", warning=True)

        self.processRequests()

    def _addVisibleLayersToQueue(self):
        for layer in sorted(self.settings.layers(), key=lambda lyr: lyr.type):
            if layer.visible:
                self.requestQueue.append(layer)

    @pyqtSlot(bool)
    def abort(self, clear_queue=True):
        if clear_queue:
            self.requestQueue.clear()

        if not self.aborted:
            self.aborted = True
            self.iface.showStatusMessage("Aborting processing...")

    @pyqtSlot()
    def quit(self):
        self.abort()
        self.iface.readyToQuit.emit()
        self.teardown()

    @pyqtSlot(bool, bool)
    def addBuildSceneTask(self, update_all=True, reload=False):
        logger.debug("Scene update requested.")

        if reload:
            r = self.RELOAD_PAGE
        elif update_all:
            r = self.BUILD_SCENE_ALL
        else:
            r = self.BUILD_SCENE

        self.requestQueue.append(r)

        if self.processingLayer:
            self.abort(clear_queue=False)
        else:
            self.processRequests()

    @pyqtSlot(Layer)
    def addBuildLayerTask(self, layer):
        logger.debug("Layer update for %s requested (visible: %s).", layer.layerId, layer.visible)

        # update layer properties and layer state in worker side export settings
        lyr = self.settings.getLayer(layer.layerId)
        if not lyr:
            return
        layer.copyTo(lyr)

        q = []
        for i in self.requestQueue:
            if isinstance(i, Layer) and i.layerId == layer.layerId:
                if not i.opt.onlyMaterial:
                    layer.opt.onlyMaterial = False
            else:
                q.append(i)

        self.requestQueue = q

        if self.processingLayer and self.processingLayer.layerId == layer.layerId:
            self.abort(clear_queue=False)
            if not self.processingLayer.opt.onlyMaterial:
                layer.opt.onlyMaterial = False

        if layer.visible:
            self.requestQueue.append(layer)

            if not self.processingLayer:
                self.processRequests()
        else:
            # immediately hide layer without adding layer to queue
            self.hideLayer(layer)

    @pyqtSlot(str, dict)
    def requestUpdateWidget(self, name, properties):
        if name == "NorthArrow":
            self.iface.runScript("setNorthArrowColor({0})".format(properties.get("color", 0)))
            self.iface.runScript("setNorthArrowVisible({0})".format(js_bool(properties.get("visible"))))

        elif name == "Label":
            self.iface.runScript('setHFLabel(pyData());', data=properties)

        else:
            return

        # TODO: do this in window.py
        self.settings.setWidgetProperties(name, properties)

    @pyqtSlot(str, object)
    def addRunScriptTask(self, string, data=None):
        self.requestQueue.append({"string": string, "data": data})

        if not self.processingLayer:
            self.processRequests()

    @pyqtSlot(ExportSettings)
    def updateExportSettings(self, settings):
        # TODO
        # if self.processingLayer:
        #    self.abort()

        # self.hideAllLayers()
        settings.copyTo(self.settings)

        # TODO: remove
        # self.iface.runScript("location.reload()")

    @pyqtSlot(bool)
    def switchCamera(self, is_ortho=False):
        self.settings.setCamera(is_ortho)
        self.iface.runScript("switchCamera({0})".format(js_bool(is_ortho)))

    @pyqtSlot(bool)
    def setNavigationEnabled(self, enabled):
        self.settings.setNavigationEnabled(enabled)
        self.iface.runScript("setNavigationEnabled({0})".format(js_bool(enabled)))

    @pyqtSlot(bool)
    def setPreviewEnabled(self, enabled):
        self.enabled = enabled
        self.iface.runScript("setPreviewEnabled({})".format(js_bool(enabled)))

        if enabled:
            self.buildScene()
        else:
            self.abort()

    @pyqtSlot(Layer)
    def addLayer(self, layer):
        layer = self.settings.addLayer(layer)
        self.buildLayer(layer)

    @pyqtSlot(str)
    def removeLayer(self, layerId):
        layer = self.settings.getLayer(layerId)
        if layer:
            self.hideLayer(layer)
            self.settings.removeLayer(layerId)

    # @pyqtSlot()
    # def updateExtent(self):
    #     if self.settings.sceneProperties().get("radioButton_FixedExtent"):
    #         return
    #     self.requestQueue.clear()
    #     if self.processingLayer:
    #         self.abort(clear_queue=False)


class Mock:

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        if DEBUG_MODE:
            logger.debug("Mock: {}".format(attr))
        return Mock

    def __bool__(self):
        return False
