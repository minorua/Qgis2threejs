# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from collections import deque
import logging

from ...conf import DEBUG_MODE, PLUGIN_NAME


logger = logging.getLogger(PLUGIN_NAME)


class SendQueue:

    def __init__(self, bridge):
        self.bridge = bridge

        self.queue = deque()
        self.isDataLoading = False

    def append(self, data):
        self.queue.append(data)

        if DEBUG_MODE and len(self.queue) > 1:
            logger.debug(f'Sending/loading data is busy. Added data: {data.get("type")}, Queue length: {len(self.queue)}')

        self.sendQueuedData()

    def removeLayer(self, jsLayerId):
        self.queue = deque([d for d in self.queue if d.get("id") != jsLayerId and d.get("layer") != jsLayerId])

    def clear(self):
        self.queue.clear()
        self.isDataLoading = False

    def dataLoaded(self):
        self.isDataLoading = False
        if self.queue:
            self.sendQueuedData()

    def sendQueuedData(self):
        if self.isDataLoading or not self.queue:
            return

        data = self.queue.popleft()

        self.isDataLoading = True
        self.bridge.sendData.emit(data, True)       # data, viaQueue

    def __len__(self):
        return len(self.queue)
