# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot

from ..exportsettings import Layer
from ...conf import DEBUG_MODE
from ...utils import logger


class Task:
    BUILD_SCENE_ALL = 1             # build scene
    BUILD_SCENE = 2                 # build scene, but do not update scene options such asbackground color, coordinates display mode and so on
    UPDATE_SCENE_OPTS = 3           # update scene options
    RELOAD_PAGE = 4
    # Layer object                  # build layer
    # {"string": str, "data": any}  # run script


class SceneLoadStatus:

    def __init__(self):
        self.reset()

    def reset(self):
        self.buildSceneStarted = False      # True if the BUILD_SCENE task has started
        self.allTasksFinalized = False
        self.taskFailed = False             # True if any task has failed


class TaskManager(QObject):

    # signals - task manager to controller
    executeTask = pyqtSignal(object)     # item: Task.BUILD_SCENE, Task.UPDATE_SCENE_OPTS, Layer, {"string": str, "data": any}
    abortCurrentTask = pyqtSignal()
    allTasksFinalized = pyqtSignal()

    def __init__(self, controller, settings):
        super().__init__(controller)
        self.controller = controller
        self._enabled = controller._enabled
        self.settings = settings

        self.timer = QTimer(self)
        self.timer.setInterval(1)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._processNextTask)

        self.initialize()

    def initialize(self):
        self.taskQueue = []
        self.resetTaskQueueCounts()

        self.isTaskRunning = False
        self.processingLayer = None
        self.sceneLoadStatus = SceneLoadStatus()

    def teardown(self):
        self.controller = None

    # task queue management
    def closeTaskQueue(self):
        self.timer.stop()
        self.timer.timeout.disconnect(self._processNextTask)

    def clearTaskQueue(self):
        self.taskQueue.clear()
        self.resetTaskQueueCounts()

    def resetTaskQueueCounts(self):
        self.totalLayerCount = 0
        self.dequeuedLayerCount = 0

    def taskQueueToString(self):
        contents = ["L:" + item.name if isinstance(item, Layer) else str(item) for item in self.taskQueue]
        return f"TaskQueue({','.join(contents)})"

    def addBuildSceneTask(self, update_all=True, reload=False):
        self.clearTaskQueue()

        if reload:
            self.taskQueue.append(Task.RELOAD_PAGE)

        else:
            self.taskQueue.append(Task.BUILD_SCENE)
            if update_all:
                self.taskQueue.append(Task.UPDATE_SCENE_OPTS)

            logger.debug("Scene build task queued.")
            self._addBuildAllLayerTasks()

        if self.isTaskRunning:
            self.abortCurrentTask.emit()
            # processNextTask is called in taskFinalized()
        else:
            self.processNextTask()

    def _addBuildAllLayerTasks(self):
        for layer in sorted(self.settings.layers(), key=lambda lyr: lyr.type):
            if layer.visible:
                self.taskQueue.append(layer)
                self.totalLayerCount += 1

    def addBuildLayerTask(self, layer):
        # If the layer being processed is the same as the layer to be added, abort processing.
        if self.processingLayer and self.processingLayer.layerId == layer.layerId:
            only_material = self.processingLayer.opt.onlyMaterial
            self.abortCurrentTask.emit()

            # Inherit onlyMaterial=False from the aborted layer
            if not only_material:
                layer.opt.onlyMaterial = False

        # Remove existing Layer with the same layerId from the queue.
        # If any removed layer has onlyMaterial=False, propagate it to the new layer.
        new_queue = []
        for item in self.taskQueue:
            if isinstance(item, Layer) and item.layerId == layer.layerId:
                if not item.opt.onlyMaterial:
                    layer.opt.onlyMaterial = False

                self.totalLayerCount -= 1
                continue

            new_queue.append(item)

        self.taskQueue = new_queue
        self.taskQueue.append(layer)
        self.totalLayerCount += 1

        logger.debug(f"Layer build task queued for {layer.name}.")

        self.processNextTask()

    def removeBuildLayerTask(self, layer):
        # If the layer being processed is the same as the layer to be removed, abort processing.
        if self.processingLayer and self.processingLayer.layerId == layer.layerId:
            self.abortCurrentTask.emit()

        task_count = len(self.taskQueue)
        self.taskQueue = [i for i in self.taskQueue if not (isinstance(i, Layer) and i.layerId == layer.layerId)]
        if len(self.taskQueue) < task_count:
            self.totalLayerCount -= 1

    def addRunScriptTask(self, string, data=None):
        self.taskQueue.append({"string": string, "data": data})

        self.processNextTask()

    def addReloadPageTask(self):
        self.addBuildSceneTask(reload=True)

    # task processing
    def processNextTask(self):
        if not self._enabled or self.isTaskRunning:
            return

        self.timer.stop()

        if self.taskQueue:
            self.timer.start()

    def _processNextTask(self):
        if not self._enabled or self.isTaskRunning or not self.taskQueue:
            return

        if DEBUG_MODE:
            logger.debug(self.taskQueueToString())

        item = self.taskQueue.pop(0)
        if item == Task.BUILD_SCENE:
            self.sceneLoadStatus.reset()
            self.sceneLoadStatus.buildSceneStarted = True

        elif isinstance(item, Layer):
            self.dequeuedLayerCount += 1

        self.isTaskRunning = True
        self.executeTask.emit(item)

        self.processNextTask()

    @pyqtSlot()
    def taskCompleted(self, _v=None):
        """Called when a scene or layer build task completes."""
        logger.debug("Task completed.")

        self.taskFinalized()

    @pyqtSlot(str, str)
    def taskFailed(self, target, traceback_str):
        """Called when a layer build task fails."""
        msg = f"Failed to build {target}."
        logger.error(f"{msg}:\n{traceback_str}")

        self.sceneLoadStatus.taskFailed = True
        self.taskFinalized()

    @pyqtSlot()
    def taskAborted(self):
        logger.debug("Task aborted.")

        self.taskFinalized()

    def taskFinalized(self, _=None):
        self.isTaskRunning = False
        self.processingLayer = None

        if self.taskQueue:
            self.processNextTask()
            return

        self.resetTaskQueueCounts()

        self.sceneLoadStatus.allTasksFinalized = True
        self.allTasksFinalized.emit()
