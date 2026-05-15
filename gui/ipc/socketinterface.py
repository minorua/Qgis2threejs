# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import ctypes
import json
import logging

from PyQt6.QtCore import QBuffer, QByteArray, QDataStream, QIODevice, QObject, QSharedMemory, QUuid, pyqtSignal, qDebug

from ...conf import DEBUG_MODE, PLUGIN_NAME

logger = logging.getLogger(PLUGIN_NAME)


class SocketInterface(QObject):

    # message type
    TYPE_NOTIFICATION = "NTF"
    TYPE_REQUEST = "REQ"
    TYPE_RESPONSE = "RES"

    # notification for common use
    DATA_RECEIVED = "_DR"       # params={"key": memory_key}

    # signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    notified = pyqtSignal(str, dict, bytes)                 # method, params
    requestReceived = pyqtSignal(int, str, dict, bytes)     # id, method, params, payload
    responseReceived = pyqtSignal(int, str, dict, bytes)    # id, reqMethod, params, payload

    def __init__(self, parent, serverName):
        QObject.__init__(self, parent)

        self.conn = None
        self.serverName = serverName

        self._id_counter = 0
        self._mem = {}

        self._buffer = QByteArray()
        self._target_size = 0

        self._callbacks = {}

    def _next_id(self):
        self._id_counter += 1
        return self._id_counter

    def createMessageBytes(self, msg_dict):
        json_bytes = json.dumps(msg_dict).encode("utf-8")

        buffer = QByteArray()
        stream = QDataStream(buffer, QIODevice.OpenModeFlag.WriteOnly)
        stream.writeInt32(len(json_bytes))
        stream.writeRawData(json_bytes)
        return buffer

    def handleIncomingMessage(self):
        b = self.conn.readAll()
        if DEBUG_MODE:
            logger.debug(f"Incoming msg size: {len(b):,}")
        self._buffer.append(b)

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

    def processJsonData(self, raw_data):
        try:
            json_str = bytes(raw_data).decode("utf-8")
            data = json.loads(json_str)

            data_type = data.get("type")
            id = data.get("id")
            method = data.get("method")
            params = data.get("params", {})

            if DEBUG_MODE:
                logger.debug(f"[-->][{data_type}:{id or ''}] {method} - {str(params)[:80]}")

            payload = b""
            payload_dict = data.get("payload", {})
            if payload_dict:
                key = payload_dict.get("key")
                size = payload_dict.get("size", 0)
                try:
                    payload = self.readSharedMemory(key)[:size]
                except Exception as e:
                    logger.error(f"Error reading shared memory: {e}")

                logger.debug(f"payload: {payload[:40]}")

                self.notify(self.DATA_RECEIVED, {"key": key})

            if data_type == self.TYPE_NOTIFICATION:
                if method == self.DATA_RECEIVED:
                    self.destroySharedMemory(params.get("key"))
                else:
                    self.notified.emit(method, params, payload)

            elif data_type == self.TYPE_REQUEST:
                self.requestReceived.emit(id, method, params, payload)

            elif data_type == self.TYPE_RESPONSE:
                self.responseReceived.emit(id, method, params, payload)
                if id in self._callbacks:
                    callback = self._callbacks.pop(id)

                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")

        except json.JSONDecodeError as e:
            print(f"Error parsing json: {e}")

        except Exception as e:
            print(f"Unexpected error: {e}")

    def createSharedMemory(self, data):
        assert isinstance(data, bytes), f"Unexpected data type ({type(data).__name__})"

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

    def _send(self, msg_type, id, method, params=None, payload=None):
        if not self.conn:
            logger.debug(f"No connection. Failed to send {method} {msg_type}.")
            return False

        if DEBUG_MODE:
            logger.debug(f"[<--][{msg_type}:{id or ''}] {method} - {str(params)[:80]}")

        msg = {
            "type": msg_type,
            "method": method
        }

        if id is not None:
            msg["id"] = id

        if params is not None:
            assert isinstance(params, dict), "Unexpected params type."
            msg["params"] = params

        if payload is not None:
            qDebug(f"payload: {payload[:20]}")

            if isinstance(payload, dict):
                data = json.dumps(payload).encode("utf-8")
            else:
                data = payload

            assert isinstance(payload, bytes), "Unexpected payload data type."

            msg["payload"] = {
                "key": self.createSharedMemory(data),
                "size": len(data)
            }

        self.conn.write(self.createMessageBytes(msg))
        self.conn.flush()
        return True

    def notify(self, method, params=None, payload=None):
        return self._send(self.TYPE_NOTIFICATION, id=None, method=method, params=params, payload=payload)

    def request(self, method, params=None, payload=None, callback=None):
        id = self._next_id()

        if callback:
            self._callbacks[id] = callback

        return self._send(self.TYPE_REQUEST, id=id, method=method, params=params, payload=payload)

    def respond(self, id, method, params=None, payload=None):
        return self._send(self.TYPE_RESPONSE, id=id, method=method, params=params, payload=payload)
