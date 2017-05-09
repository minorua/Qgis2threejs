# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DConnector

                              -------------------
        begin                : 2016-05-24
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
from PyQt5.QtCore import QObject, pyqtSignal


class Q3DConnector(QObject):

  # signals
  notified = pyqtSignal(dict)                         # params
  requestReceived = pyqtSignal(dict)                  # params
  responseReceived = pyqtSignal(bytes, dict)          # data, meta
  #TODO: data = bytes or str

  def __init__(self, parent):
    QObject.__init__(self, parent)
    self.other = None

  def connect(self, other):
    """connect to other connector"""
    self.other = other
    other.other = self

  def notify(self, params):
    if not self.other:
      return False
    self.log("Sending Notification. code: {0}".format(params.get("code")))
    self.other.receiveNotification(params)
    return True

  def request(self, params):
    if not self.other:
      return False
    self.log("Sending Request. dataType: {0}, renderId: {1}".format(params.get("dataType"), params.get("renderId")))
    self.other.receiveRequest(params)
    return True

  #TODO: support both str and bytes
  def respond(self, byteArray, meta=None):
    if not self.other:
      return False
    self.log("Sending Response. dataType: {0}, renderId: {1}".format(meta.get("dataType"), meta.get("renderId")))
    self.other.receiveResponse(byteArray, meta or {})
    return True

  def receiveNotification(self, params):
    self.notified.emit(params)

  def receiveRequest(self, params):
    self.requestReceived.emit(params)

  def receiveResponse(self, data, meta):
    lines = data.split(b"\n")
    for line in lines[:5]:
      self.log(line[:76])
    if len(lines) > 5:
      self.log("--Total {0} Lines Received--".format(len(lines)))
    self.responseReceived.emit(data, meta)

  def log(self, msg):
    print(msg)
