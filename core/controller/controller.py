# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

from collections import deque
from qgis.PyQt.QtCore import QEventLoop, QObject, QTimer, QThread, pyqtSignal, pyqtSlot
from qgis.core import Qgis, QgsProject

from .taskqueue import Task, TaskQueue
from ..build.builder import ThreeJSBuilder
from ..const import LayerType, ScriptFile
from ..exportsettings import ExportSettings, Layer
from ...conf import DEBUG_MODE, TEMP_DEBUG_MODE
from ...utils import hex_color, js_bool, logger, noop


class Q3DControllerInterface(QObject):

    # signals - controller iface to builder
    buildSceneRequest = pyqtSignal(ExportSettings)
    buildLayerRequest = pyqtSignal(Layer, ExportSettings)
    quitRequest = pyqtSignal()

    def __init__(self, controller, webPage, viewIface=None):
        super().__init__(parent=controller)

        self.controller = controller
        self.builder = controller.builder
        self.webPage = webPage
        self.viewIface = viewIface

        # delegating methods
        self.runScript = viewIface.runScript if viewIface else noop
        self.loadScriptFiles = viewIface.loadScriptFiles if viewIface else noop

    def teardown(self):
        self.controller = None
        self.builder = None

    def setupConnections(self):
        """Setup signal-slot connections between controller interface, builder, and 3D view interface."""
        # web page -> controller
        self.webPage.loadFinished.connect(self.controller.pageLoaded)

        # web bridge -> controller
        self.webPage.bridge.initialized.connect(self.controller.viewerInitialized)
        self.webPage.bridge.dataLoaded.connect(self.controller.dataLoaded)

        # controller interface -> builder
        self.buildSceneRequest.connect(self.builder.buildSceneSlot)
        self.buildLayerRequest.connect(self.builder.buildLayerSlot)

        # builder -> controller
        self.builder.dataReady.connect(self.controller.appendDataToSendQueue)
        self.builder.taskCompleted.connect(self.controller.taskCompleted)
        self.builder.taskFailed.connect(self.controller.taskFailed)
        self.builder.taskAborted.connect(self.controller.taskAborted)
        self.builder.progressUpdated.connect(self.controller.builderProgressUpdated)

    def teardownConnections(self):
        signals = [
            # web page
            self.webPage.loadFinished,
            # web bridge
            self.webPage.bridge.initialized,
            self.webPage.bridge.dataLoaded,
            # builder
            self.buildSceneRequest,
            self.buildLayerRequest,
            self.builder.dataReady,
            self.builder.taskCompleted,
            self.builder.taskFailed,
            self.builder.taskAborted,
            self.builder.progressUpdated
        ]

        for signal in signals:
            signal.disconnect()

    def requestBuildScene(self, settings):
        self.buildSceneRequest.emit(settings)

    def requestBuildLayer(self, layer, settings):
        self.buildLayerRequest.emit(layer, settings)

    def loadScriptFile(self, scriptFileId, force=False):
        self.loadScriptFiles([scriptFileId], force)


class Q3DController(QObject):

    # signals
    statusMessage = pyqtSignal(str, int)         # message, timeout_ms
    progressUpdated = pyqtSignal(int, int, str)  # current, total, msg
    allTasksFinished = pyqtSignal()

    def __init__(self, parent, settings, webPage, viewIface=None, useThread=False, enabledAtStart=True):
        super().__init__(parent)

        if settings is None:
            defaultSettings = {}
            settings = ExportSettings()
            settings.loadSettings(defaultSettings)

            err_msg = settings.checkValidity()
            if err_msg:
                logger.warning("Invalid settings: " + err_msg)

        self.settings = settings        # hold a reference to the original settings
        self.settingsUpdated = True
        self._settingsCopy = None

        self.webPage = webPage
        self.offScreen = bool(viewIface is None)

        self.builder = ThreeJSBuilder(parent=None if useThread else self,
                                      isInUiThread=not useThread)
        self.builder.setObjectName("threeJSBuilder")

        self.thread = None
        if useThread:
            self.thread = QThread(self)
            self.thread.setObjectName("builderThread")

            # move builder to worker thread and start event loop
            if DEBUG_MODE:
                assert self.builder.parent() is None

            self.builder.moveToThread(self.thread)
            self.thread.start()

        self.iface = Q3DControllerInterface(self, webPage, viewIface)
        self.iface.setObjectName("controllerInterface")

        self._enabled = enabledAtStart
        self.isBuilderBusy = False
        self.processingLayer = None
        self.currentProgress = -1

        self.taskQueue = TaskQueue(settings)

        self.timer = QTimer(self)
        self.timer.setInterval(1)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._processNextTask)

        self.sendQueue = deque()
        self.isDataLoading = False

        # delegating method
        self.runScript = webPage.runScript

    def closeTaskQueue(self):
        self._enabled = False

        self.timer.stop()
        self.timer.timeout.disconnect(self._processNextTask)

        self.taskQueue.clear()

    def teardown(self):
        self.abort()

        if self.thread:
            # Send a quit request to the builder so that it returns to the main thread.
            self.iface.quitRequest.connect(self.builder.quit)

            loop = QEventLoop()
            self.builder.readyToQuit.connect(loop.quit)
            QTimer.singleShot(0, self.iface.quitRequest.emit)   # emit quit request in next event loop
            loop.exec()

            # stop worker thread event loop
            self.thread.quit()
            self.thread.wait()

            self.builder.deleteLater()

        self.iface.teardown()

    @property
    def aborted(self):
        return self.builder.aborted

    @aborted.setter
    def aborted(self, value):
        self.builder.aborted = value

    def abort(self, clear_queue=True, show_msg=False):
        logger.debug(f"Q3DController: aborting. clear queue({clear_queue})")

        if clear_queue:
            self.taskQueue.clear()

        if not self.aborted:
            if show_msg:
                self.showStatusMessage("Aborting processing...")

            self.builder.abort()

    def pageLoaded(self, ok):
        logger.debug("Page load finished.")
        if self.webPage.url().scheme() != "file":
            return

        # configuration
        if self.settings.isOrthoCamera():
            self.runScript("Q3D.Config.orthoCamera = true;")

        p = self.settings.widgetProperties("NorthArrow")
        if p.get("visible"):
            self.runScript("Q3D.Config.northArrow.enabled = true;")
            self.runScript("Q3D.Config.northArrow.color = {};".format(hex_color(p.get("color", 0), prefix="0x")))

        if not self.settings.isNavigationEnabled():
            self.runScript("Q3D.Config.navigation.enabled = false;")

        self.runScript("init({}, {}, {}, {})".format(js_bool(self.offScreen),
                                                     DEBUG_MODE,
                                                     Qgis.QGIS_VERSION_INT,
                                                     js_bool(self.webPage.isWebEnginePage)))

    def viewerInitialized(self):
        if not self.enabled:
            self.runScript("setPreviewEnabled(false)")

        # labels
        header = self.settings.headerLabel()
        footer = self.settings.footerLabel()
        if header or footer:
            self.runScript('setHFLabel(pyData())', data={"Header": header, "Footer": footer})

        # crs check
        if QgsProject.instance().crs().isGeographic():
            self.webPage.showMessageBar("Current CRS is a geographic coordinate system. Please change it to a projected coordinate system.", warning=True)

        self.clearStatusMessage()

        if self.enabled:
            self.runScript("app.start()")
            self.addBuildSceneTask()

    @pyqtSlot(dict)
    def appendDataToSendQueue(self, data):
        self.sendQueue.append(data)

        if DEBUG_MODE and len(self.sendQueue) > 1:
            logger.warning(f"Sending/loading data is busy. Queue length: {len(self.sendQueue)}")

        self.sendQueuedData()

    @pyqtSlot()
    def dataLoaded(self):
        self.isDataLoading = False
        self.sendQueuedData()

    def sendQueuedData(self):
        if self.sendQueue and not self.isDataLoading:
            self.webPage.sendData(self.sendQueue.popleft())
            self.isDataLoading = True

    def buildScene(self):
        if self.isBuilderBusy:
            logger.info("Previous processing is still in progress. Cannot start to build scene.")
            return False

        self.isBuilderBusy = True
        self.iface.requestBuildScene(self._settingsCopy)
        return True

    def updateSceneOptions(self):
        sp = self.settings.sceneProperties()

        # outline effect
        self.runScript("setOutlineEffectEnabled({})".format(js_bool(sp.get("checkBox_Outline"))))

        # update background color
        params = "{0}, 1".format(hex_color(sp.get("colorButton_Color", 0), prefix="0x")) if sp.get("radioButton_Color") else "0, 0"
        self.runScript("setBackgroundColor({0})".format(params))

        # coordinate display
        self.runScript("Q3D.Config.coord.visible = {};".format(js_bool(self.settings.coordDisplay())))

        latlon = self.settings.isCoordLatLon()
        self.runScript("Q3D.Config.coord.latlon = {};".format(js_bool(latlon)))
        if latlon:
            self.iface.loadScriptFile(ScriptFile.PROJ4)

    def buildLayer(self, layer):
        if isinstance(layer, dict):
            layer = Layer.fromDict(layer)

        if self.isBuilderBusy:
            logger.info(f'Previous processing is still in progress. Cannot start to build layer "{layer.name}".')
            return False

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
        self.iface.requestBuildLayer(layer, self._settingsCopy)

        if len(self.settings.layers(export_only=True)) == 1:
            self.addRunScriptTask("adjustCameraPos()")

        return True

    def hideLayer(self, layer):
        """hide layer and remove all objects from the layer"""
        # If the layer is being processed, abort processing.
        if self.processingLayer and self.processingLayer.layerId == layer.layerId:
            self.abort(clear_queue=False)

        self.taskQueue.removeBuildLayerTask(layer)
        self.runScript(f'hideLayer("{layer.jsLayerId}", true)')

    @pyqtSlot()
    def taskCompleted(self, _v=None):
        logger.debug("Task completed.")

        self.taskFinalized()

    @pyqtSlot(str, str)
    def taskFailed(self, target, traceback_str):
        msg = f"Failed to build {target}."
        logger.error(f"{msg}:\n{traceback_str}")

        self.showStatusMessage(msg, timeout_ms=5000)
        self.taskFinalized()

    @pyqtSlot()
    def taskAborted(self):
        logger.debug("Task aborted.")

        self.taskFinalized()

    def taskFinalized(self):
        self.isBuilderBusy = False
        self.processingLayer = None

        self.clearStatusMessage()

        if self.taskQueue:
            self._processNextTask()

        else:
            self.taskQueue.resetCounts()

            # wait until data loading are done
            self.runScript("allDataSent()", callback=self._hideProgress)

    def _hideProgress(self, _v=None):
        self.allTasksFinished.emit()

    @pyqtSlot(int, int, str)
    def builderProgressUpdated(self, current, total, msg):
        if TEMP_DEBUG_MODE:
            logger.debug(f"{current} / {total} ({msg}) Dequeued: {self.taskQueue.dequeuedLayerCount}, Total: {self.taskQueue.totalLayerCount}")

        if total * self.taskQueue.totalLayerCount == 0:
            p = self.currentProgress
        else:
            p = int((total * (self.taskQueue.dequeuedLayerCount - 1) + current) / (total * self.taskQueue.totalLayerCount) * 100)

        p = max(0, min(100, p))
        if self.currentProgress != p or msg:
            self.currentProgress = p
            self.progressUpdated.emit(p, 100, msg)

        self.runScript(f"updateProgressBar({current}, {total})")

    def processNextTask(self):
        if self.isBuilderBusy:
            return

        self.timer.stop()

        if self.taskQueue:
            self.timer.start()

    def _processNextTask(self):
        if not self._enabled or self.isBuilderBusy or not self.taskQueue:
            return

        self.aborted = False

        if self.settings.isUpdated():
            self._settingsCopy = self.settings.clone()
            self.settings.clearUpdatedFlag()

        if DEBUG_MODE:
            logger.debug(self.taskQueue)

        try:
            item = self.taskQueue.pop()
            if item == Task.RELOAD_PAGE:
                self.runScript("location.reload()")

            elif item == Task.BUILD_SCENE:
                self.buildScene()

            elif item == Task.UPDATE_SCENE_OPTS:
                self.updateSceneOptions()

            elif isinstance(item, Layer):
                if self.settings.getLayer(item.layerId):
                    if item.visible:
                        self.buildLayer(item)
                    else:
                        self.hideLayer(item)
                else:
                    logger.info(f"Layer {item.layerId} not found in settings. Ignored.")

            elif isinstance(item, dict):
                self.runScript(item.get("string"), data=item.get("data"), callback=self.taskCompleted)

            else:
                logger.warning(f"Unknown task: {item}")

        except Exception as _:
            import traceback
            logger.warning(traceback.format_exc())

            self.webPage.showMessageBar("One or more errors occurred. See log messages panel in QGIS main window for details.", warning=True)

        self.processNextTask()

    def addBuildSceneTask(self, update_all=True, reload=False):
        self.taskQueue.addBuildSceneTask(update_all=update_all, reload=reload)

        if self.isBuilderBusy:
            self.abort(clear_queue=False)
            # scene-building task will run after aborting in taskFinalized()
        else:
            self.processNextTask()

    def addBuildLayerTask(self, layer):
        # If the layer being processed is the same as the layer to be added, abort processing.
        if self.processingLayer and self.processingLayer.layerId == layer.layerId:
            only_material = self.processingLayer.opt.onlyMaterial
            self.abort(clear_queue=False)

            # Inherit onlyMaterial=False from the aborted layer
            if not only_material:
                layer.opt.onlyMaterial = False

        self.taskQueue.addBuildLayerTask(layer)
        self.processNextTask()

    def updateWidget(self, name, properties):
        if name == "NorthArrow":
            self.runScript("setNorthArrowColor({})".format(properties.get("color", 0)))
            self.runScript("setNorthArrowVisible({})".format(js_bool(properties.get("visible"))))

        elif name == "Label":
            self.runScript('setHFLabel(pyData());', data=properties)

        else:
            return

    def addRunScriptTask(self, string, data=None):
        self.taskQueue.addRunScriptTask(string, data=data)
        self.processNextTask()

    def reload(self):
        self.runScript("location.reload()")

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        if self._enabled == value:
            return

        self._enabled = value

        self.runScript("setPreviewEnabled({})".format(js_bool(self._enabled)))

        if self._enabled:
            self.addBuildSceneTask()
        else:
            self.abort()

    @pyqtSlot(bool)
    def setEnabled(self, enabled):
        self.enabled = enabled

    def cameraState(self, flat=False):
        return self.runScript("cameraState({})".format(1 if flat else 0), wait=True)

    def setCameraState(self, state):
        """set camera position and camera target"""
        self.runScript("setCameraState(pyData())", data=state)

    def resetCameraState(self):
        self.runScript("app.controls.reset()")

    def showStatusMessage(self, msg, timeout_ms=0):
        self.statusMessage.emit(msg, timeout_ms)

    def clearStatusMessage(self):
        self.statusMessage.emit("", 0)

    def progress(self, current=0, total=100, msg=""):
        self.progressUpdated.emit(current, total, msg)


class Mock:

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        if DEBUG_MODE:
            logger.debug("Mock: {}".format(attr))
        return Mock

    def __bool__(self):
        return False
