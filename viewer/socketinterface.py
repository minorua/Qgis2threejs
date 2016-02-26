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
import os

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
  notified = pyqtSignal(int, dict)
  requestReceived = pyqtSignal(int, dict)
  responseReceived = pyqtSignal("QByteArray", int)

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
      self.log("--Message Received--")
      self.log(json_str)

      obj = json.loads(json_str)
      msgType = obj["type"]
      if msgType == self.TYPE_NOTIFICATION:
        if obj["code"] == self.N_DATA_RECEIVED:
          memKey = obj["params"]["memoryKey"]
          mem = self._mem[memKey]
          if mem.isAttached():
            mem.detach()
            self.log("Shared memory detached: key={0}".format(memKey))
          del self._mem[memKey]
        else:
          self.notified.emit(obj["code"], obj["params"])

      elif msgType == self.TYPE_REQUEST:
        self.requestReceived.emit(obj["dataType"], obj["params"])

      elif msgType == self.TYPE_RESPONSE:
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

        if os.name == "nt":
          ba = ba.replace(b"\0", b"")

        for line in ba.data().split(b"\n"):
          self.log(line[:256])

        self.notify(self.N_DATA_RECEIVED, {"memoryKey": obj["memoryKey"]})
        self.responseReceived.emit(ba, obj["dataType"])

  def notify(self, code, params=None):
    if not self.conn:
      return False
    obj = {"type": self.TYPE_NOTIFICATION, "code": code, "params": params or {}}
    self.conn.write(json.dumps(obj).encode("utf-8") + b"\n")
    self.conn.flush()
    return True

  def request(self, dataType, params=None):
    if not self.conn:
      return False
    obj = {"type": self.TYPE_REQUEST, "dataType": dataType, "params": params or {}}
    self.conn.write(json.dumps(obj).encode("utf-8") + b"\n")
    self.conn.flush()
    return True

  def respond(self, byteArray, dataType):
    if not self.conn:
      return False
    obj = {"type": self.TYPE_RESPONSE, "dataType": dataType}
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
