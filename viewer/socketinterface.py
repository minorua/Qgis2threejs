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

try:
  from PyQt5.QtCore import QBuffer, QByteArray, QObject, QSharedMemory, QTextStream, pyqtSignal
except:
  from PyQt4.QtCore import QBuffer, QByteArray, QObject, QSharedMemory, QTextStream, pyqtSignal


class SocketInterface(QObject):

  # message type
  TYPE_NOTIFICATION = 1
  TYPE_REQUEST = 2
  TYPE_RESPONSE = 3

  # internal notification
  N_DATA_RECEIVED = -1

  # signals
  notified = pyqtSignal(dict)                         # params
  requestReceived = pyqtSignal(dict)                  # params
  responseReceived = pyqtSignal("QByteArray", dict)   # data, meta

  def __init__(self, serverName, keyCount=5, parent=None):
    QObject.__init__(self, parent)

    self.serverName = serverName
    self.keyCount = keyCount
    self.conn = None

    self._index = 0
    self._mem = {}

  def log(self, msg):
    pass

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
        self.log("Notification Received. code: {0}".format(obj["params"].get("code")))
        if obj["params"].get("code") == self.N_DATA_RECEIVED:
          memKey = obj["params"]["memoryKey"]
          mem = self._mem[memKey]
          if mem.isAttached():
            mem.detach()
            self.log("Shared memory detached: key={0}".format(memKey))
          del self._mem[memKey]
        else:
          self.notified.emit(obj["params"])

      elif msgType == self.TYPE_REQUEST:
        self.log("Request Received. dataType: {0}, renderId: {1}".format(obj["params"].get("dataType"), obj["params"].get("renderId")))
        self.requestReceived.emit(obj["params"])

      elif msgType == self.TYPE_RESPONSE:
        self.log("Response Received. dataType: {0}, renderId: {1}".format(obj["meta"].get("dataType"), obj["meta"].get("renderId")))
        mem = QSharedMemory(obj["memoryKey"])
        if not mem.attach(QSharedMemory.ReadOnly):
          self.log("Cannot attach this process to the shared memory segment: {0}".format(mem.errorString()))
          return

        size = mem.size()
        self.log("Size of memory segment is {0} bytes.".format(size))

        mem.lock()
        ba = QByteArray()
        buffer = QBuffer(ba)
        buffer.setData(mem.constData())
        mem.unlock()
        mem.detach()

        lines = ba.data().split(b"\n")
        for line in lines[:5]:
          self.log(line[:76])
        if len(lines) > 5:
          self.log("--Total {0} Lines Received--".format(len(lines)))

        self.notify({"code": self.N_DATA_RECEIVED, "memoryKey": obj["memoryKey"]})
        self.responseReceived.emit(ba, obj["meta"])

  def notify(self, params):
    if not self.conn:
      return False
    self.log("Sending Notification. code: {0}".format(params.get("code")))
    obj = {"type": self.TYPE_NOTIFICATION, "params": params}
    self.conn.write(json.dumps(obj).encode("utf-8") + b"\n")
    self.conn.flush()
    return True

  def request(self, params):
    if not self.conn:
      return False
    self.log("Sending Request. dataType: {0}, renderId: {1}".format(params.get("dataType"), params.get("renderId")))
    obj = {"type": self.TYPE_REQUEST, "params": params}
    self.conn.write(json.dumps(obj).encode("utf-8") + b"\n")
    self.conn.flush()
    return True

  def respond(self, byteArray, meta=None):
    if not self.conn:
      return False
    self.log("Sending Response. dataType: {0}, renderId: {1}".format(meta.get("dataType"), meta.get("renderId")))
    obj = {"type": self.TYPE_RESPONSE, "meta": meta or {}}

    memKey = self.nextMemoryKey()
    obj["memoryKey"] = memKey
    # TODO: check that the memory segment is not used

    # store data in shared memory
    mem = QSharedMemory(memKey)
    if mem.isAttached():
      mem.detach()

    if not mem.create(byteArray.size()):
      self.log(mem.errorString())
      return False
    self.log("Shared memory created: {0}, {1} bytes".format(memKey, byteArray.size()))

    mem.lock()
    try:
      ctypes.memmove(int(mem.data()), byteArray.data(), byteArray.size())
    finally:
      mem.unlock()

    self._mem[memKey] = mem

    self.conn.write(json.dumps(obj).encode("utf-8") + b"\n")
    self.conn.flush()
    return True
