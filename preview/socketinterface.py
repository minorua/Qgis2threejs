# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SocketInterface

                                                            -------------------
                begin                : 2016-02-10
                copyright            : (C) 2016 Minoru Akagi
                email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import ctypes
import json
import logging as logger

from PyQt6.QtCore import QBuffer, QByteArray, QObject, QSharedMemory, QTextStream, pyqtSignal


class SocketInterface(QObject):

    # message type
    TYPE_NOTIFICATION = 1
    TYPE_REQUEST = 2
    TYPE_RESPONSE = 3

    # internal notification
    N_DATA_RECEIVED = -1

    # signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    notified = pyqtSignal(dict)                         # params
    requestReceived = pyqtSignal(dict)                  # params
    responseReceived = pyqtSignal(bytes, dict)          # data, meta

    def __init__(self, serverName, keyCount=5, parent=None):
        QObject.__init__(self, parent)

        self.serverName = serverName
        self.keyCount = keyCount
        self.conn = None

        self._index = 0
        self._mem = {}

    def nextMemoryKey(self):
        self._index = 0 if self._index == self.keyCount - 1 else self._index + 1
        return self.serverName + str(self._index)

    def receiveMessage(self):
        stream = QTextStream(self.conn)
        if stream.atEnd():
            return
        data = stream.readAll()

        for json_str in data.split("\n")[:-1]:
            obj = json.loads(json_str)
            msgType = obj["type"]
            if msgType == self.TYPE_NOTIFICATION:
                logger.info("Notification Received. code: {}".format(obj["params"].get("code")))
                if obj["params"].get("code") == self.N_DATA_RECEIVED:
                    memKey = obj["params"]["memoryKey"]
                    mem = self._mem[memKey]
                    if mem.isAttached():
                        mem.detach()
                        logger.info("Shared memory detached: key=" + memKey)
                    del self._mem[memKey]
                else:
                    self.notified.emit(obj["params"])

            elif msgType == self.TYPE_REQUEST:
                logger.info("Request Received. dataType: {}, renderId: {}".format(obj["params"].get("dataType"), obj["params"].get("renderId")))
                self.requestReceived.emit(obj["params"])

            elif msgType == self.TYPE_RESPONSE:
                logger.info("Response Received. dataType: {}, renderId: {}".format(obj["meta"].get("dataType"), obj["meta"].get("renderId")))
                mem = QSharedMemory(obj["memoryKey"])
                if not mem.attach(QSharedMemory.ReadOnly):
                    logger.error("Cannot attach this process to the shared memory segment: " + mem.errorString())
                    return

                size = mem.size()
                logger.info(f"Size of memory segment is {size} bytes.")

                mem.lock()
                ba = QByteArray()
                buffer = QBuffer(ba)
                buffer.setData(mem.constData())
                mem.unlock()
                mem.detach()

                data = ba.data()
                lines = data.split(b"\n")
                for line in lines[:5]:
                    logger.info(line[:76])
                if len(lines) > 5:
                    logger.info(f"--Total {len(lines)} Lines Received--")

                self.notify({"code": self.N_DATA_RECEIVED, "memoryKey": obj["memoryKey"]})
                self.responseReceived.emit(data, obj["meta"])

    def notify(self, params):
        if not self.conn:
            return False
        logger.info("Sending Notification. code: {}".format(params.get("code")))
        obj = {"type": self.TYPE_NOTIFICATION, "params": params}
        self.conn.write(json.dumps(obj).encode("utf-8") + b"\n")
        self.conn.flush()
        return True

    def request(self, params):
        if not self.conn:
            return False
        logger.info("Sending Request. dataType: {}, renderId: {}".format(params.get("dataType"), params.get("renderId")))
        obj = {"type": self.TYPE_REQUEST, "params": params}
        self.conn.write(json.dumps(obj).encode("utf-8") + b"\n")
        self.conn.flush()
        return True

    #TODO: support both str and bytes
    #TODO: rename byteArray to data
    def respond(self, byteArray, meta=None):
        if not self.conn:
            return False
        logger.info("Sending Response. dataType: {}, renderId: {}".format(meta.get("dataType"), meta.get("renderId")))
        obj = {"type": self.TYPE_RESPONSE, "meta": meta or {}}

        memKey = self.nextMemoryKey()
        obj["memoryKey"] = memKey
        # TODO: check that the memory segment is not used

        # store data in shared memory
        mem = QSharedMemory(memKey)
        if mem.isAttached():
            mem.detach()

        if not mem.create(len(byteArray)):
            logger.error(mem.errorString())
            return False
        logger.info(f"Shared memory created: {memKey}, {len(byteArray)} bytes")

        mem.lock()
        try:
            ctypes.memmove(int(mem.data()), byteArray, len(byteArray))
        finally:
            mem.unlock()

        self._mem[memKey] = mem

        self.conn.write(json.dumps(obj).encode("utf-8") + b"\n")
        self.conn.flush()
        return True
