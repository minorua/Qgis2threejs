# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

from qgis.PyQt.QtCore import QObject, QTimer, QThread, pyqtSignal, pyqtSlot

from ..build.builder import ThreeJSBuilder
from ..const import LayerType, ScriptFile
from ..exportsettings import ExportSettings, Layer
from ...conf import DEBUG_MODE
from ...utils import hex_color, js_bool, logger, noop


class Q3DControllerInterface(QObject):

    # signals - controller iface to builder
    buildSceneRequest = pyqtSignal()
    buildLayerRequest = pyqtSignal(object)       # Layer
    quitRequest = pyqtSignal()

    def __init__(self, controller, viewIface=None):
        super().__init__(parent=controller)

        self.controller = controller
        self.builder = controller.builder
        self.viewIface = viewIface

        # delegating methods
        self.runScript = viewIface.runScript if viewIface else noop
        self.loadScriptFiles = viewIface.loadScriptFiles if viewIface else noop

    def teardown(self):
        self.controller = None
        self.builder = None

    def setupConnections(self):
        """Setup signal-slot connections between controller interface, builder, and 3D view interface."""
        # controller interface -> builder
        self.buildSceneRequest.connect(self.builder.buildSceneSlot)
        self.buildLayerRequest.connect(self.builder.buildLayerSlot)

        # builder -> controller
        self.builder.taskCompleted.connect(self.controller.taskFinalized)
        self.builder.taskAborted.connect(self.controller.taskFinalized)

        # builder -> 3D view interface
        if self.viewIface:
            self.builder.dataReady.connect(self.viewIface.sendData)

    def teardownConnections(self):
        signals = [
            # builder
            self.buildSceneRequest,
            self.buildLayerRequest,
            self.builder.dataReady,
            self.builder.taskCompleted,
            self.builder.taskAborted,
        ]

        for signal in signals:
            signal.disconnect()

    def requestBuildScene(self):
        self.buildSceneRequest.emit()

    def requestBuildLayer(self, layer):
        self.buildLayerRequest.emit(layer)

    def loadScriptFile(self, scriptFileId, force=False):
        self.loadScriptFiles([scriptFileId], force)

    def showMessageBar(self, msg, timeout_ms=0, warning=False):
        """show message bar at top of web view"""
        self.runScript(f"showMessageBar(pyData(), {timeout_ms}, {js_bool(warning)})", data=msg)


class Q3DController(QObject):

    # task types
    BUILD_SCENE_ALL = 1     # build scene
    BUILD_SCENE = 2         # build scene, but do not update scene options such asbackground color, coordinates display mode and so on
    UPDATE_SCENE_OPTS = 3   # update scene options
    RELOAD_PAGE = 4

    # signals
    statusMessage = pyqtSignal(str, int)    # message, timeout_ms
    progressUpdated = pyqtSignal(int, str)  # percentage, msg

    def __init__(self, parent=None, settings=None, viewIface=None, useThread=False):
        super().__init__(parent)

        if settings is None:
            defaultSettings = {}
            settings = ExportSettings()
            settings.loadSettings(defaultSettings)

            err_msg = settings.checkValidity()
            if err_msg:
                logger.warning("Invalid settings: " + err_msg)

        self.settings = settings
        self.builder = ThreeJSBuilder(self, settings, isInUiThread=not useThread)

        self.thread = None
        if useThread:
            self.thread = QThread(self)

            # move builder to worker thread and start event loop
            self.builder.moveToThread(self.thread)
            self.thread.start()

        self.iface = Q3DControllerInterface(self, viewIface)
        self.iface.setObjectName("controllerInterface")

        self._enabled = True
        self.aborted = False
        self.isBuilderBusy = False
        self.processingLayer = None

        self.taskQueue = []
        self.timer = QTimer(self)
        self.timer.setInterval(1)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._processNextTask)

    def closeTaskQueue(self):
        self._enabled = False

        self.timer.stop()
        self.timer.timeout.disconnect(self._processNextTask)

        self.taskQueue.clear()

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

    def abort(self, clear_queue=True, show_msg=False):
        if clear_queue:
            self.taskQueue.clear()

        if show_msg and not self.aborted:
            self.showStatusMessage("Aborting processing...")

        self.aborted = True
        self.builder.abort()

    def buildScene(self):
        if self.isBuilderBusy:
            logger.info("Previous processing is still in progress. Cannot start to build scene.")
            return False

        self.progress(0, "Building scene")
        self.isBuilderBusy = True
        self.iface.requestBuildScene()
        return True

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

        if self.isBuilderBusy:
            logger.info('Previous processing is still in progress. Cannot start to build layer "{}".'.format(layer.name))
            return False

        pmsg = "Building {0}...".format(layer.name)
        self.progress(0, pmsg)

        if layer.type == LayerType.POINT and layer.properties.get("comboBox_ObjectType") == "3D Model":
            self.iface.loadScriptFiles([ScriptFile.COLLADALOADER,
                                        ScriptFile.GLTFLOADER])

        elif layer.type == LayerType.LINESTRING and layer.properties.get("comboBox_ObjectType") == "Thick Line":
            self.iface.loadScriptFiles([ScriptFile.MESHLINE])

        elif layer.type == LayerType.POINTCLOUD:
            self.iface.loadScriptFiles([ScriptFile.FETCH,
                                        ScriptFile.POTREE,
                                        ScriptFile.PCLAYER])

        self.processingLayer = layer
        self.isBuilderBusy = True
        self.iface.requestBuildLayer(layer)

        if len(self.settings.layersToExport()) == 1:
            self.addRunScriptTask("adjustCameraPos()")

        return True

    def hideLayer(self, layer):
        """hide layer and remove all objects from the layer"""
        self.iface.runScript('hideLayer("{}", true)'.format(layer.jsLayerId))

    def hideAllLayers(self):
        """hide all layers and remove all objects from the layers"""
        self.iface.runScript("hideAllLayers(true)")

    def taskFinalized(self):
        self.isBuilderBusy = False
        self.processingLayer = None

        self.progress()
        self.clearStatusMessage()

        self._processNextTask()

    def processNextTask(self):
        self.timer.stop()

        if DEBUG_MODE:
            contents = ["L:" + item.name if isinstance(item, Layer) else str(item) for item in self.taskQueue]
            logger.debug(f"Task queue: {', '.join(contents)}")

        if self.taskQueue:
            self.timer.start()

    def _processNextTask(self):
        if not self._enabled or self.isBuilderBusy or not self.taskQueue:
            return

        self.aborted = False

        try:
            if self.RELOAD_PAGE in self.taskQueue:
                self.taskQueue.clear()
                self.iface.runScript("location.reload()")

            elif self.BUILD_SCENE_ALL in self.taskQueue:
                self.taskQueue.clear()
                self.taskQueue.append(self.UPDATE_SCENE_OPTS)
                self._addVisibleLayersToQueue()

                self.buildScene()

            elif self.BUILD_SCENE in self.taskQueue:
                self.taskQueue.clear()
                self._addVisibleLayersToQueue()

                self.buildScene()

            else:
                item = self.taskQueue.pop(0)
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
                    logger.warning(f"Unknown task: {item}")

        except Exception as e:
            import traceback
            logger.warning(traceback.format_exc())

            self.iface.showMessageBar("One or more errors occurred. See log messages panel in QGIS main window for details.", warning=True)

        self.processNextTask()

    def _addVisibleLayersToQueue(self):
        for layer in sorted(self.settings.layers(), key=lambda lyr: lyr.type):
            if layer.visible:
                self.taskQueue.append(layer)

    def addBuildSceneTask(self, update_all=True, reload=False):
        logger.debug("Scene build task queued.")

        if reload:
            r = self.RELOAD_PAGE
        elif update_all:
            r = self.BUILD_SCENE_ALL
        else:
            r = self.BUILD_SCENE

        self.taskQueue.append(r)

        if self.isBuilderBusy:
            # TODO: clear queue and add a new task?
            self.abort(clear_queue=False)
        else:
            self.processNextTask()

    def addBuildLayerTask(self, layer):
        logger.debug(f"Layer build task queued for {layer.name} (visible: {layer.visible}).")

        q = []
        for i in self.taskQueue:
            if isinstance(i, Layer) and i.layerId == layer.layerId:
                if not i.opt.onlyMaterial:
                    layer.opt.onlyMaterial = False
            else:
                q.append(i)

        self.taskQueue = q

        if self.processingLayer and self.processingLayer.layerId == layer.layerId:
            self.abort(clear_queue=False)
            if not self.processingLayer.opt.onlyMaterial:
                layer.opt.onlyMaterial = False

        if layer.visible:
            self.taskQueue.append(layer)

            if not self.isBuilderBusy:
                self.processNextTask()
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
        self.taskQueue.append({"string": string, "data": data})

        if not self.isBuilderBusy:
            self.processNextTask()

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

    # @pyqtSlot()
    # def updateExtent(self):
    #     if self.settings.sceneProperties().get("radioButton_FixedExtent"):
    #         return
    #     self.requestQueue.clear()
    #     if self.isBuilderBusy:
    #         self.abort(clear_queue=False)

    def showStatusMessage(self, msg, timeout_ms=0):
        self.statusMessage.emit(msg, timeout_ms)

    def clearStatusMessage(self):
        self.statusMessage.emit("", 0)

    def progress(self, percentage=100, msg=""):
        self.progressUpdated.emit(int(percentage), msg)


class Mock:

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        if DEBUG_MODE:
            logger.debug("Mock: {}".format(attr))
        return Mock

    def __bool__(self):
        return False
