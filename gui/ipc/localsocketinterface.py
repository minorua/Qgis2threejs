# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import ctypes
import logging

from PyQt6.QtCore import QBuffer, QByteArray, QDataStream, QIODevice, QObject, QSharedMemory, QUuid

from .socketinterface import SocketInterface
from ...conf import PLUGIN_NAME

logger = logging.getLogger(PLUGIN_NAME)


class LocalSocketInterface(SocketInterface):

    def __init__(self, parent, serverName):
        SocketInterface.__init__(self, parent)

        self.serverName = serverName

        self._buffer = QByteArray()
        self._target_size = 0

        self._mem = {}

    def createMessageBytes(self, msg_dict):
        json_bytes = super().createMessageBytes(msg_dict)

        buffer = QByteArray()
        stream = QDataStream(buffer, QIODevice.OpenModeFlag.WriteOnly)
        stream.writeInt32(len(json_bytes))
        stream.writeRawData(json_bytes)
        return buffer

    def handleIncomingMessage(self):
        self._buffer.append(self.sock.readAll())

        while True:
            if self._target_size == 0:
                if self._buffer.size() < 4:
                    break

                self._target_size = QDataStream(self._buffer.left(4)).readInt32()
                self._buffer.remove(0, 4)

            if self._buffer.size() < self._target_size:
                break

            raw_data = self._buffer.left(self._target_size)
            self._buffer.remove(0, self._target_size)

            self.processJsonData(raw_data)

            self._target_size = 0

            if self._buffer.isEmpty():
                break

    def createSharedMemory(self, data: bytes):
        key = QUuid.createUuid().toString(QUuid.StringFormat.WithoutBraces)[:8]
        mem = QSharedMemory(key)

        if not mem.create(len(data)):
            logger.error("Error creating shared memory: " + mem.errorString())
            return False

        mem.lock()
        try:
            ctypes.memmove(int(mem.data()), data, len(data))
        finally:
            mem.unlock()

        self._mem[key] = mem

        logger.debug("Shared memory created: key=" + key)
        return key

    def destroySharedMemory(self, key):
        self._mem[key].detach()
        logger.debug("Shared memory detached: key=" + key)
        del self._mem[key]

    def readSharedMemory(self, key):
        mem = QSharedMemory(key)
        if not mem.attach(QSharedMemory.AccessMode.ReadOnly):
            logger.error("Cannot attach this process to the shared memory segment: " + mem.errorString())
            return

        size = mem.size()
        logger.debug(f"Payload size: {size:,}")

        ba = QByteArray()
        buffer = QBuffer(ba)

        mem.lock()
        buffer.setData(mem.constData())
        mem.unlock()
        mem.detach()
        return ba.data()

    def writeToSocket(self, data):
        if self.sock:
            self.sock.write(data)
            self.sock.flush()
