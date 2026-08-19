# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import json
import logging

from PyQt6.QtCore import QObject, pyqtSignal, qDebug

from ...conf import DEBUG_MODE, PLUGIN_NAME

logger = logging.getLogger(PLUGIN_NAME)


class SocketInterface(QObject):

    # message type
    TYPE_COMMAND = "CMD"
    TYPE_EVENT = "EVT"
    TYPE_REQUEST = "REQ"
    TYPE_RESPONSE = "RES"

    # method
    DATA_RECEIVED = "_DR"       # params={"key": memory_key}

    # signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    commandReceived = pyqtSignal(str, dict, bytes)          # method, params, payload
    eventReceived = pyqtSignal(str, dict, bytes)            # method, params, payload
    requestReceived = pyqtSignal(int, str, dict, bytes)     # id, method, params, payload
    responseReceived = pyqtSignal(int, str, dict, bytes)    # id, reqMethod, params, payload

    def __init__(self, parent):
        QObject.__init__(self, parent)

        self.sock = None

        self._id_counter = 0
        self._callbacks = {}

    def _next_id(self):
        self._id_counter += 1
        return self._id_counter

    def createMessageBytes(self, msg_dict: dict) -> bytes:
        return json.dumps(msg_dict).encode("utf-8")

    def writeToSocket(self, data: bytes):
        if self.sock:
            self.sock.write(data)
            self.sock.flush()

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

                self.sendEvent(self.DATA_RECEIVED, {"key": key})

            match data_type:
                case self.TYPE_COMMAND:
                    self.commandReceived.emit(method, params, payload)

                case self.TYPE_EVENT:
                    if method == self.DATA_RECEIVED:
                        self.destroySharedMemory(params.get("key"))
                    else:
                        self.eventReceived.emit(method, params, payload)

                case self.TYPE_REQUEST:
                    self.requestReceived.emit(id, method, params, payload)

                case self.TYPE_RESPONSE:
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

    def _send(self, msg_type, id, method, params: dict | None = None, payload: bytes | dict | None = None) -> bool:
        if not self.sock:
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
            msg["params"] = params

        if payload is not None:
            qDebug(f"payload: {payload[:20]}")

            if isinstance(payload, dict):
                data = json.dumps(payload).encode("utf-8")
            else:
                data = payload

            msg["payload"] = {
                "key": self.createSharedMemory(data),
                "size": len(data)
            }

        self.writeToSocket(self.createMessageBytes(msg))
        return True

    def sendCommand(self, method, params=None, payload=None):
        return self._send(self.TYPE_COMMAND, id=None, method=method, params=params, payload=payload)

    def sendEvent(self, method, params=None, payload=None):
        return self._send(self.TYPE_EVENT, id=None, method=method, params=params, payload=payload)

    def sendRequest(self, method, params=None, payload=None, callback=None):
        id = self._next_id()

        if callback:
            self._callbacks[id] = callback

        return self._send(self.TYPE_REQUEST, id=id, method=method, params=params, payload=payload)

    def sendResponse(self, id, method, params=None, payload=None):
        return self._send(self.TYPE_RESPONSE, id=id, method=method, params=params, payload=payload)
