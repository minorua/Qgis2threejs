# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

from qgis.PyQt.QtCore import QEventLoop, QObject, QTimer, QThread, pyqtSignal, pyqtSlot
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
    quitRequest = pyqtSignal()

    # signals - controller iface to viewer iface
    dataSent = pyqtSignal(dict)                  # data
    scriptSent = pyqtSignal(str, object, str)    # script, data, msg_shown_in_log_panel
    statusMessage = pyqtSignal(str, int)         # message, timeout_ms
    progressUpdated = pyqtSignal(int, str)       # percentage, msg
    loadScriptsRequest = pyqtSignal(list, bool)  # list of script ID, force (if False, do not load a script that is already loaded)

    def __init__(self, controller):
        super().__init__(parent=controller)

        self.controller = controller
        self.builder = controller.builder
        self.viewIface = None

    def teardown(self):
        self.controller = None
        self.builder = None
        self.viewIface = None

    def setupConnections(self, iface):
        """Setup signal-slot connections between controller interface, builder, and viewer interface.
        Args:
            iface: web view side interface (Q3DInterface or its subclass)
        """
        # controller interface -> builder
        self.buildSceneRequest.connect(self.builder.buildSceneSlot)
        self.buildLayerRequest.connect(self.builder.buildLayerSlot)

        # builder -> viewer interface
        # TODO:
        self.builder.dataReady.connect(self.dataSent)

        # builder -> controller
        self.builder.taskCompleted.connect(self.controller.taskCompleted)

        # controller interface -> viewer interface
        self.viewIface = iface

        self.dataSent.connect(iface.sendJSONObject)
        self.scriptSent.connect(iface.runScript)
        self.loadScriptsRequest.connect(iface.loadScriptFiles)
        self.statusMessage.connect(iface.statusMessage)
        self.progressUpdated.connect(iface.progressUpdated)

        # viewer interface -> controller
        if hasattr(iface, "layerAdded"):
            iface.layerAdded.connect(self.controller.addLayer)
            iface.layerRemoved.connect(self.controller.removeLayer)

    def teardownConnections(self):
        signals = [
            # builder
            self.buildSceneRequest,
            self.buildLayerRequest,
            self.builder.dataReady,
            self.builder.taskCompleted,
            # viewer interface
            self.dataSent,
            self.scriptSent,
            self.loadScriptsRequest,
            self.statusMessage,
            self.progressUpdated
        ]

        if hasattr(self.viewIface, "layerAdded"):
            signals += [
                self.viewIface.layerAdded,
                self.viewIface.layerRemoved
            ]

        for signal in signals:
            signal.disconnect()

    def requestBuildScene(self):
        self.buildSceneRequest.emit()

    def requestBuildLayer(self, layer):
        self.buildLayerRequest.emit(layer)

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

            # move builder to worker thread and start event loop
            self.builder.moveToThread(self.thread)
            self.thread.start()

        self.iface = Q3DControllerInterface(self)
        self.iface.setObjectName("controllerInterface")

        self._enabled = True
        self.aborted = False  # processing aborted flag
        self.processingLayer = None
        self.mapCanvas = None

        self.requestQueue = []
        self.timer = QTimer(self)
        self.timer.setInterval(1)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._processRequests)

        # delegating method
        self.setupConnections = self.iface.setupConnections

    def teardown(self):
        self.abort()

        if self.thread:
            # TODO: remove this redundant code
            # send quit request to the builder and wait until the builder gets ready to quit
            # self.iface.quitRequest.connect(self.builder.quit)

            # loop = QEventLoop()
            # self.builder.readyToQuit.connect(loop.quit)
            # QTimer.singleShot(0, self.iface.quitRequest.emit)
            # loop.exec()

            # stop worker thread event loop
            self.thread.quit()
            self.thread.wait()

        self.iface.teardown()

    def teardownConnections(self):
        self.timer.stop()
        self.timer.timeout.disconnect(self._processRequests)

        self.iface.teardownConnections()

    def abort(self, clear_queue=True, show_msg=False):
        if clear_queue:
            self.requestQueue.clear()

        if show_msg and not self.aborted:
            self.iface.showStatusMessage("Aborting processing...")

        self.aborted = True

        # TODO: builder.abort()

    # @pyqtSlot(QPainter)
    def _requestBuildScene(self, _=None):
        self.addBuildSceneTask(update_all=False)

    def buildScene(self):
        if self.processingLayer:
            logger.info("Previous processing is still in progress. Cannot start to build scene.")
            return False

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

        if DEBUG_MODE:
            contents = ["L:" + item.name if isinstance(item, Layer) else str(item) for item in self.requestQueue]
            logger.debug(f"Request queue: {', '.join(contents)}")

        if self.requestQueue:
            self.timer.start()

    def _processRequests(self):
        if not self.enabled or self.processingLayer or not self.requestQueue:
            return

        self.aborted = False

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
                    if self.settings.getLayer(item.layerId):
                        if item.visible:
                            self.buildLayer(item)
                        else:
                            self.hideLayer(item)
                    else:
                        logger.info(f"Layer {item.layerId} not found in settings. Ignored.")

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

    def addBuildLayerTask(self, layer):
        logger.debug("Layer update for %s requested (visible: %s).", layer.layerId, layer.visible)

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

    def updateWidget(self, name, properties):
        if name == "NorthArrow":
            self.iface.runScript("setNorthArrowColor({})".format(properties.get("color", 0)))
            self.iface.runScript("setNorthArrowVisible({})".format(js_bool(properties.get("visible"))))

        elif name == "Label":
            self.iface.runScript('setHFLabel(pyData());', data=properties)

        else:
            return

    @pyqtSlot(str, object)
    def addRunScriptTask(self, string, data=None):
        self.requestQueue.append({"string": string, "data": data})

        if not self.processingLayer:
            self.processRequests()

    def updateExportSettings(self, settings=None, mapSettings=None, layer=None):
        if settings:
            self.settings = settings.clone()

        # TODO: clone mapSettings?
        if mapSettings:
            self.settings.setMapSettings(mapSettings)

        if layer:
            lyr = self.settings.getLayer(layer.layerId)
            if lyr:
                layer.copyTo(lyr)

    def reload(self):
        self.iface.runScript("location.reload()")

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        if self._enabled == value:
            return

        self._enabled = value

        self.iface.runScript("setPreviewEnabled({})".format(js_bool(self._enabled)))

        if self._enabled:
            self.addBuildSceneTask()
        else:
            self.abort()

    @pyqtSlot(Layer)
    def addLayer(self, layer):
        layer = self.settings.addLayer(layer)
        self.addBuildLayerTask(layer)

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
