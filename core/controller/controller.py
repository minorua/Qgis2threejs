# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

from collections import deque
from functools import wraps
from qgis.PyQt.QtCore import QEventLoop, QObject, QTimer, QThread, pyqtSignal, pyqtSlot
from qgis.core import Qgis, QgsProject

from .taskmanager import Task, TaskManager
from ..build.builder import ThreeJSBuilder
from ..const import LayerType, ScriptFile
from ..exportsettings import ExportSettings, Layer
from ...conf import DEBUG_MODE
from ...utils import hex_color, js_bool, logger


# decorator to skip method execution when the object the method belongs to is disabled
def requires_enabled(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if not self._enabled:
            return
        return func(self, *args, **kwargs)
    return wrapper


class ConnectionManager:

    def __init__(self, controller, webPage):
        self.controller = controller
        self.builder = controller.builder
        self.webPage = webPage

    def setup(self):
        """Setup signal-slot connections between controller interface, builder, and 3D view interface."""
        # web page -> controller
        self.webPage.loadFinished.connect(self.controller.pageLoaded)

        # web bridge -> controller
        self.webPage.bridge.initialized.connect(self.controller.viewerInitialized)
        self.webPage.bridge.dataLoaded.connect(self.controller.dataLoaded)

        # controller -> builder
        self.controller.buildSceneRequest.connect(self.builder.buildSceneSlot)
        self.controller.buildLayerRequest.connect(self.builder.buildLayerSlot)

        # task manager -> controller
        self.controller.taskManager.executeTask.connect(self.controller.executeTask)
        self.controller.taskManager.abortCurrentTask.connect(self.controller.abortCurrentTask)
        self.controller.taskManager.allTasksFinalized.connect(self.controller.allTasksFinalized)

        # builder -> controller
        self.builder.dataReady.connect(self.controller.appendDataToSendQueue)
        self.builder.progressUpdated.connect(self.controller.builderProgressUpdated)

        # builder -> task manager
        self.builder.taskCompleted.connect(self.controller.taskManager.taskCompleted)
        self.builder.taskFailed.connect(self.controller.taskManager.taskFailed)
        self.builder.taskAborted.connect(self.controller.taskManager.taskAborted)

    def teardown(self):
        signals = [
            self.webPage.loadFinished,
            self.webPage.bridge.initialized,
            self.webPage.bridge.dataLoaded,
            self.controller.buildSceneRequest,
            self.controller.buildLayerRequest,
            self.controller.taskManager.executeTask,
            self.controller.taskManager.abortCurrentTask,
            self.controller.taskManager.allTasksFinalized,
            self.builder.dataReady,
            self.builder.progressUpdated,
            self.builder.taskCompleted,
            self.builder.taskFailed,
            self.builder.taskAborted
        ]

        for signal in signals:
            signal.disconnect()

        self.controller = None


class Q3DController(QObject):

    # signals
    statusMessage = pyqtSignal(str, int)         # message, timeout_ms
    progressUpdated = pyqtSignal(int, int, str)  # current, total, msg

    # signals - controller to builder
    buildSceneRequest = pyqtSignal(ExportSettings)
    buildLayerRequest = pyqtSignal(Layer, ExportSettings)
    quitRequest = pyqtSignal()                   # request the builder to move back to the main thread

    def __init__(self, parent, settings, webPage, offScreen=False, useThread=False, enabledAtStart=True):
        super().__init__(parent)

        self.webPage = webPage
        self.offScreen = offScreen
        self._enabled = enabledAtStart

        # settings
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

        # builder and thread management
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

        # connections
        self.conn = ConnectionManager(self, webPage)

        # task management
        self.taskManager = TaskManager(self, settings)
        self.taskManager.setObjectName("taskManager")

        # data dispatching
        self.sendQueue = deque()
        self.isDataLoading = False

        # progress
        self.currentProgress = -1

    def teardown(self):
        if not self.aborted:
            self.abort()

        self.taskManager.teardown()

        if self.thread:
            # Send a quit request to the builder so that it returns to the main thread.
            self.quitRequest.connect(self.builder.quit)

            loop = QEventLoop()
            self.builder.readyToQuit.connect(loop.quit)
            QTimer.singleShot(0, self.quitRequest.emit)   # emit quit request in next event loop
            loop.exec()

            # stop worker thread event loop
            self.thread.quit()
            self.thread.wait()

            self.builder.deleteLater()

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        if self._enabled == value:
            return

        self._enabled = value
        self.taskManager._enabled = value

    @property
    def aborted(self):
        return self.builder.aborted

    @aborted.setter
    def aborted(self, value):
        self.builder.aborted = value

    @pyqtSlot(bool)
    def abort(self, clear_tasks=True, show_msg=False):
        logger.debug(f"Controller: aborting. clear queue({clear_tasks})")

        if clear_tasks:
            self.taskManager.clearTaskQueue()
            self.taskManager.taskSequenceStatus.reset()

        if not self.aborted:
            if show_msg:
                self.showStatusMessage("Aborting processing...", timeout_ms=2000)

            self.builder.abort()

        self.clearSendQueue()

    def close(self):
        self.enabled = False
        self.abort()
        self.taskManager.closeTaskQueue()

    def pageLoaded(self, ok):
        logger.debug("Page load finished.")

        self.taskManager.initialize()
        self.clearSendQueue()

        if self.webPage.url().scheme() != "file":
            return

        configs = []
        if self.settings.isOrthoCamera():
            configs.append("Q3D.Config.orthoCamera = true;")

        p = self.settings.widgetProperties("NorthArrow")
        if p.get("visible"):
            configs.append("Q3D.Config.northArrow.enabled = true;")
            configs.append("Q3D.Config.northArrow.color = {};".format(hex_color(p.get("color", 0), prefix="0x")))

        if not self.settings.isNavigationEnabled():
            configs.append("Q3D.Config.navigation.enabled = false;")

        if configs:
            self.runScript("\n".join(configs))

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
            self.sendData({"type": "labels",
                           "Header": header,
                           "Footer": footer})
        # crs check
        if QgsProject.instance().crs().isGeographic():
            self.webPage.showMessageBar("Current CRS is a geographic coordinate system. Please change it to a projected coordinate system.", warning=True)

        self.clearStatusMessage()

        if self.enabled:
            self.runScript("app.start()")
            self.taskManager.addBuildSceneTask()

    def updateSettingsCopyIfNeeded(self):
        if self.settings.isUpdated() or self._settingsCopy is None:
            self._settingsCopy = self.settings.clone()
            self.settings.clearUpdatedFlag()

    @pyqtSlot(object)
    def executeTask(self, task):
        if not self._enabled:
            return

        self.aborted = False

        try:
            if task == Task.RELOAD_PAGE:
                self.webPage.reload()

            elif task == Task.BUILD_SCENE:
                self.buildScene()

            elif task == Task.UPDATE_SCENE_OPTS:
                self.updateSceneOptions(callback=self.taskManager.taskFinalized)

            elif isinstance(task, Layer):   # BUILD_LAYER
                if self.settings.getLayer(task.layerId):
                    if task.visible:
                        self.buildLayer(task)
                    else:
                        self.hideLayer(task, callback=self.taskManager.taskFinalized)
                else:
                    logger.info(f"Layer {task.layerId} not found in settings. Ignored.")

            elif isinstance(task, dict):    # RUN_SCRIPT or SEND_DATA
                if task.get("type") == "script":
                    self.runScript(task.get("script"), callback=self.taskManager.taskFinalized)
                else:
                    self.appendDataToSendQueue(data=task)
                    self.taskManager.taskFinalized()
            else:
                logger.warning(f"Unknown task: {task}")

        except Exception as _:
            import traceback
            logger.error(f"Error while processing task {task}:\n{traceback.format_exc()}")

    @pyqtSlot()
    def abortCurrentTask(self):
        self.abort(clear_tasks=False)

    @pyqtSlot()
    def allTasksFinalized(self):
        logger.debug("All tasks finalized.")

        # send a special data item that represents the final item in a sequence of tasks.
        signal = {
            "type": "signal",
            "name": "queueCompleted",
            "success": not self.taskManager.taskSequenceStatus.taskFailed,
            "is_scene": self.taskManager.taskSequenceStatus.buildSceneStarted
        }
        self.appendDataToSendQueue(data=signal)

    def buildScene(self):
        self.updateSettingsCopyIfNeeded()
        self.buildSceneRequest.emit(self._settingsCopy)

    def updateSceneOptions(self, callback=None):
        sp = self.settings.sceneProperties()
        lines = []

        # outline effect
        lines.append("setOutlineEffectEnabled({});".format(js_bool(sp.get("checkBox_Outline"))))

        # update background color
        params = "{}, 1".format(hex_color(sp.get("colorButton_Color", 0), prefix="0x")) if sp.get("radioButton_Color") else "0, 0"
        lines.append("setBackgroundColor({});".format(params))

        # coordinate display
        lines.append("Q3D.Config.coord.visible = {};".format(js_bool(self.settings.coordDisplay())))

        latlon = self.settings.isCoordLatLon()
        lines.append("Q3D.Config.coord.latlon = {};".format(js_bool(latlon)))

        if latlon:
            self.loadScriptFiles([ScriptFile.PROJ4])

        self.runScript("\n".join(lines), callback=callback)

    def buildLayer(self, layer):
        self.taskManager.processingLayer = layer

        files = []
        if layer.type == LayerType.POINT and layer.properties.get("comboBox_ObjectType") == "3D Model":
            files = [ScriptFile.COLLADALOADER,
                     ScriptFile.GLTFLOADER]

        elif layer.type == LayerType.LINESTRING and layer.properties.get("comboBox_ObjectType") == "Thick Line":
            files = [ScriptFile.MESHLINE]

        elif layer.type == LayerType.POINTCLOUD:
            files = [ScriptFile.FETCH,
                     ScriptFile.POTREE,
                     ScriptFile.PCLAYER]

        if files:
            self.loadScriptFiles(files, callback=lambda: self._buildLayer(layer))
        else:
            self._buildLayer(layer)

    def _buildLayer(self, layer):
        self.updateSettingsCopyIfNeeded()
        self.buildLayerRequest.emit(layer, self._settingsCopy)

        if len(self.settings.layers(export_only=True)) == 1:
            self.taskManager.addRunScriptTask("adjustCameraPos()")

    def hideLayer(self, layer, callback=None):
        """hide layer and remove all objects from the layer"""
        self.taskManager.removeBuildLayerTask(layer)        # abort if being processed and remove pending task for the layer
        self.runScript(f'hideLayer("{layer.jsLayerId}", true)', callback=callback)

    # send queue management
    @pyqtSlot(dict)
    def appendDataToSendQueue(self, data):
        self.sendQueue.append(data)

        if DEBUG_MODE and len(self.sendQueue) > 1:
            logger.debug(f"Sending/loading data is busy. Added data: {data.get("type", "Unknown")}, Queue length: {len(self.sendQueue)}")

        self.sendQueuedData()

    def clearSendQueue(self):
        self.sendQueue.clear()
        self.isDataLoading = False

    @pyqtSlot()
    def dataLoaded(self):
        self.isDataLoading = False
        if self.sendQueue:
            self.sendQueuedData()

    def sendQueuedData(self):
        if self.isDataLoading or not self.sendQueue:
            return

        data = self.sendQueue.popleft()
        if data.get("type") == "signal" and data.get("name") == "queueCompleted":
            self.taskManager.taskSequenceStatus.reset()

        self.isDataLoading = True
        self.sendData(data, viaQueue=True)

    # web page access methods
    def updateWidget(self, name, properties):
        if name == "NorthArrow":
            self.runScript("setNorthArrowColor({})".format(properties.get("color", 0)))
            self.runScript("setNorthArrowVisible({})".format(js_bool(properties.get("visible"))))

        elif name == "Label":
            self.sendData({"type": "labels",
                           "Header": properties.get("Header", ""),
                           "Footer": properties.get("Footer", "")})
        else:
            return

    def cameraState(self, flat=False):
        return self.runScript("cameraState({})".format(1 if flat else 0), wait=True)

    def setCameraState(self, state):
        """set camera position and its target"""
        self.sendData({"type": "cameraState",
                       "state": state})

    def resetCameraState(self):
        self.runScript("app.controls.reset()")

    # status and progress
    def showStatusMessage(self, msg, timeout_ms=0):
        self.statusMessage.emit(msg, timeout_ms)

    def clearStatusMessage(self):
        self.statusMessage.emit("", 0)

    def progress(self, current=0, total=100, msg=""):
        self.progressUpdated.emit(current, total, msg)

    @pyqtSlot(int, int, str)
    def builderProgressUpdated(self, current, total, msg):
        # if DEBUG_MODE:
        #    logger.debug(f"{current} / {total} ({msg}) Dequeued: {self.taskManager.dequeuedLayerCount}, Total: {self.taskManager.totalLayerCount}")

        total = total or 100
        if self.taskManager.totalLayerCount:
            p = int((total * (self.taskManager.dequeuedLayerCount - 1) + current) / (total * self.taskManager.totalLayerCount) * 100)
        else:
            p = self.currentProgress

        p = max(0, min(100, p))
        if self.currentProgress != p or msg:
            self.currentProgress = p
            self.progressUpdated.emit(p, 100, msg)

    @requires_enabled
    def sendData(self, data, viaQueue=False):
        self.webPage.sendData(data, viaQueue)

    @requires_enabled
    def runScript(self, string, message="", sourceID="controller.py", callback=None, wait=False):
        return self.webPage.runScript(string, message, sourceID, callback, wait)

    @requires_enabled
    def loadScriptFiles(self, script_ids, callback=None):
        self.webPage.loadScriptFiles(script_ids, callback=callback)
