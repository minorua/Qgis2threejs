# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass

from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from ..exportsettings import BuildOptions, BuildDEMOptions, Layer
from ...conf import DEBUG_MODE
from ...utils.logging import logger


class Task:
    BUILD_SCENE_ALL = 1             # build scene
    BUILD_SCENE = 2                 # build scene, but do not update scene options such asbackground color, coordinates display mode and so on
    UPDATE_SCENE_OPTS = 3           # update scene options
    RELOAD_PAGE = 4
    # BuildLayerTask
    # BUildTileTask                         # build tile
    # {"type": "...", ...}                  # send data
    # {"type": "script", "script": "..."}   # run script


@dataclass
class BuildLayerTask:

    def __init__(self, layer: Layer, options: BuildDEMOptions | None = None):
        self.layer = layer
        self.options = options or BuildOptions()

    def __repr__(self):
        return f"L:{self.layer.name}"


@dataclass
class BuildTileTask:

    url: str
    layer: Layer
    level: int
    x: int
    y: int
    onlyMaterial: bool

    @staticmethod
    def fromUrl(url, settings):
        tileUrl, _, args = url.partition("?")
        onlyMaterial = bool(args == "mtl")

        jsLayerId, level, x, y = map(int, tileUrl.removesuffix(".tile").rsplit("/", 4)[-4:])

        layer = settings.getLayerByJSLayerId(jsLayerId)
        if layer is None:
            logger.warning(f"Layer not found: {jsLayerId}")
            return None

        return BuildTileTask(url, layer, level, x, y, onlyMaterial)

    def __repr__(self):
        return f'Tile: {self.layer.jsLayerId}/{self.level}/{self.x}/{self.y}{" (mtl)" if self.onlyMaterial else ""})'


class TaskSequenceStatus:

    def __init__(self):
        self.reset()

    def reset(self):
        self.buildSceneStarted = False      # True if the BUILD_SCENE task has started
        self.allTasksFinalized = False
        self.taskFailed = False             # True if any task has failed


class TaskManager(QObject):

    # signals - task manager to controller
    executeTask = pyqtSignal(object)     # item: Task.BUILD_SCENE, Task.UPDATE_SCENE_OPTS, Layer, BuildTileTask, {"string": str, "data": any}
    abortCurrentTask = pyqtSignal()
    allTasksFinalized = pyqtSignal()

    def __init__(self, controller, settings):
        super().__init__(controller)
        self.controller = controller
        self.settings = settings
        self.enabled = True

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._processNextTask)

        self.initialize()

    def initialize(self):
        self.taskQueue = []
        self.resetCounters()

        self.isTaskRunning = False
        self.runningBuildLayerTask = None
        self.taskSequenceStatus = TaskSequenceStatus()

    def teardown(self):
        self.controller = None

    # task queue management
    def closeTaskQueue(self):
        self.timer.stop()
        self.timer.timeout.disconnect(self._processNextTask)

    def clearTaskQueue(self):
        self.taskQueue.clear()
        self.resetCounters()

    def resetCounters(self):
        self.queuedBuildTaskCounter = 0
        self.dequeuedBuildTaskCounter = 0

    def taskQueueToString(self):
        contents = [str(task) for task in self.taskQueue]
        return f"TaskQueue({','.join(contents)})"

    def addBuildSceneTask(self, update_all=True):
        self.clearTaskQueue()
        self.taskQueue.append(Task.BUILD_SCENE)
        self.queuedBuildTaskCounter += 1
        if update_all:
            self.taskQueue.append(Task.UPDATE_SCENE_OPTS)

        logger.debug("Scene build task queued.")
        self._addBuildAllLayerTasks()

        if self.isTaskRunning:
            self.abortCurrentTask.emit()            # processNextTask is called in taskFinalized()
        else:
            self.processNextTask()

    def _addBuildAllLayerTasks(self):
        for layer in sorted(self.settings.layers(), key=lambda lyr: lyr.type):
            if layer.visible:
                self.taskQueue.append(BuildLayerTask(layer))
                self.queuedBuildTaskCounter += 1

    def addBuildLayerTask(self, layer, options=None):
        options = options or BuildOptions()

        # If the layer being processed is the same as the layer to be added, abort processing.
        runningTask = self.runningBuildLayerTask
        if runningTask and runningTask.layer.layerId == layer.layerId:
            if options and not runningTask.options.onlyMaterial:
                options.onlyMaterial = False

            self.abortCurrentTask.emit()

        # Remove existing Layer with the same layerId from the queue.
        # If any removed layer has onlyMaterial=False, propagate it to the new layer.
        new_queue = []
        for task in self.taskQueue:
            if isinstance(task, (BuildLayerTask, BuildTileTask)) and task.layer.layerId == layer.layerId:
                if options and not task.options.onlyMaterial:
                    options.onlyMaterial = False

                self.queuedBuildTaskCounter -= 1
            else:
                new_queue.append(task)

        self.taskQueue = new_queue
        self.taskQueue.append(BuildLayerTask(layer, options))
        self.queuedBuildTaskCounter += 1

        logger.debug(f"Layer build task queued for {layer.name}.")

        self.processNextTask()

    def removeBuildLayerTask(self, layer):
        # If the layer being processed is the same as the layer to be removed, abort processing.
        if self.runningBuildLayerTask and self.runningBuildLayerTask.layer.layerId == layer.layerId:
            self.abortCurrentTask.emit()

        new_queue = []
        for task in self.taskQueue:
            if isinstance(task, (BuildLayerTask, BuildTileTask)) and task.layer.layerId == layer.layerId:
                self.queuedBuildTaskCounter -= 1
            else:
                new_queue.append(task)

        self.taskQueue = new_queue

    def addBuildTileTask(self, task: BuildTileTask):
        self.taskQueue.append(task)
        self.queuedBuildTaskCounter += 1
        self.processNextTask()

    def addSendDataTask(self, data: dict):
        self.taskQueue.append(data)
        self.processNextTask()

    def addRunScriptTask(self, string):
        self.taskQueue.append({"type": "script", "script": string})
        self.processNextTask()

    def addReloadPageTask(self, force_reload=False):
        self.clearTaskQueue()

        if self.isTaskRunning:
            self.abortCurrentTask.emit()

        self.taskQueue.append(Task.RELOAD_PAGE)

        if force_reload:
            self.isTaskRunning = False

        self.processNextTask()

    # task processing
    def processNextTask(self):
        if not self.enabled or self.isTaskRunning:
            return

        self.timer.stop()

        if self.taskQueue:
            self.timer.start()

    def _processNextTask(self):
        if not self.enabled or self.isTaskRunning or not self.taskQueue:
            return

        # logger.debug(self.taskQueueToString())

        task = self.taskQueue.pop(0)
        if task == Task.BUILD_SCENE:
            self.taskSequenceStatus.reset()
            self.taskSequenceStatus.buildSceneStarted = True
            self.dequeuedBuildTaskCounter += 1

        elif isinstance(task, (BuildLayerTask, BuildTileTask)):
            self.dequeuedBuildTaskCounter += 1

        self.isTaskRunning = True
        self.executeTask.emit(task)

    @pyqtSlot()
    def taskCompleted(self, _v=None):
        """Called when a build task completes."""
        logger.debug("Task completed.")

        self.taskFinalized()

    @pyqtSlot(str, str)
    def taskFailed(self, target, traceback_str):
        """Called when a build task fails."""
        msg = f"Failed to build {target}."
        logger.error(f"{msg}:\n{traceback_str}")

        self.taskSequenceStatus.taskFailed = True
        self.taskFinalized()

    @pyqtSlot()
    def taskAborted(self):
        logger.debug("Task aborted.")

        self.taskFinalized()

    def taskFinalized(self, _=None):
        self.isTaskRunning = False
        self.runningBuildLayerTask = None

        if self.taskQueue:
            self.processNextTask()
            return

        self.resetCounters()

        self.taskSequenceStatus.allTasksFinalized = True
        self.allTasksFinalized.emit()
