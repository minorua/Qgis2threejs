# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from ..exportsettings import Layer
from ...utils import logger

class Task:
    BUILD_SCENE_ALL = 1     # build scene
    BUILD_SCENE = 2         # build scene, but do not update scene options such asbackground color, coordinates display mode and so on
    UPDATE_SCENE_OPTS = 3   # update scene options
    RELOAD_PAGE = 4


class TaskQueue:

    def __init__(self, settings):
        """
        Args:
        settings: ExportSettings
        """
        self.settings = settings

        self._queue = []
        self.totalLayerCount = 0
        self.dequeuedLayerCount = 0

    def clear(self):
        self._queue.clear()
        self.totalLayerCount = 0
        self.dequeuedLayerCount = 0

    def append(self, item):
        if isinstance(item, Layer):
            # Remove existing layer with the same layerId.
            self._queue = [i for i in self._queue if not (isinstance(i, Layer) and i.layerId == item.layerId)]
            self.totalLayerCount += 1

        self._queue.append(item)

    def pop(self, index=0):
        item = self._queue.pop(index)
        if isinstance(item, Layer):
            self.dequeuedLayerCount += 1
        return item

    def __bool__(self):
        return bool(self._queue)

    def __len__(self):
        return len(self._queue)

    def __iter__(self):
        return iter(self._queue)

    def __repr__(self):
        contents = ["L:" + item.name if isinstance(item, Layer) else str(item) for item in self._queue]
        return f"TaskQueue({','.join(contents)})"

    def addBuildSceneTask(self, update_all=True, reload=False):
        if Task.RELOAD_PAGE in self._queue:
            return

        self.clear()
        if reload:
            self._queue.append(Task.RELOAD_PAGE)
            return

        self._queue.append(Task.BUILD_SCENE)
        if update_all:
            self._queue.append(Task.UPDATE_SCENE_OPTS)

        logger.debug("Scene build task queued.")

        self.addBuildAllLayerTasks()

    def addBuildAllLayerTasks(self):
        for layer in sorted(self.settings.layers(), key=lambda lyr: lyr.type):
            if layer.visible:
                self.append(layer)

    def addBuildLayerTask(self, layer):
        # Remove existing Layer with the same layerId from the queue.
        # If any removed layer has onlyMaterial=False, propagate it to the new layer.
        new_queue = []
        for item in self._queue:
            if isinstance(item, Layer) and item.layerId == layer.layerId:
                if not item.opt.onlyMaterial:
                    layer.opt.onlyMaterial = False
                continue

            new_queue.append(item)

        self._queue = new_queue
        self._queue.append(layer)

        logger.debug(f"Layer build task queued for {layer.name}.")

    def removeBuildLayerTask(self, layer):
        self._queue = [i for i in self._queue if not (isinstance(i, Layer) and i.layerId == layer.layerId)]

    def addRunScriptTask(self, string, data=None):
        self._queue.append({"string": string, "data": data})
