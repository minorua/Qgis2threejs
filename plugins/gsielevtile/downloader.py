# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Downloader
   convenient class to download files which uses QGIS network settings
                              -------------------
        begin                : 2012-12-16
        copyright            : (C) 2013 by Minoru Akagi
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
from PyQt5.QtCore import QDateTime, QEventLoop, QObject, QTimer, QUrl, qDebug, pyqtSignal, pyqtSlot
from PyQt5.QtNetwork import QNetworkRequest, QNetworkReply
from qgis.core import QgsNetworkAccessManager
import threading

DEBUG_MODE = 0


class Downloader(QObject):

  # error status
  NO_ERROR = 0
  TIMEOUT_ERROR = 4
  UNKNOWN_ERROR = -1

  # PyQt signals
  replyFinished = pyqtSignal(str)
  allRepliesFinished = pyqtSignal()

  def __init__(self, parent=None, maxConnections=2, defaultCacheExpiration=24, userAgent=""):
    QObject.__init__(self, parent)

    self.maxConnections = maxConnections
    self.defaultCacheExpiration = defaultCacheExpiration    # hours
    self.userAgent = userAgent

    # initialize variables
    self.clear()
    self.sync = False

    self.eventLoop = QEventLoop()

    self.timer = QTimer()
    self.timer.setSingleShot(True)
    self.timer.timeout.connect(self.timeOut)

  def clear(self):
    self.queue = []
    self.requestingReplies = {}
    self.fetchedFiles = {}

    self._successes = 0
    self._errors = 0
    self._cacheHits = 0

    self.errorStatus = Downloader.NO_ERROR

  def _replyFinished(self):
    reply = self.sender()
    url = reply.request().url().toString()
    if url not in self.fetchedFiles:
      self.fetchedFiles[url] = None

    if url in self.requestingReplies:
      del self.requestingReplies[url]

    httpStatusCode = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
    if reply.error() == QNetworkReply.NoError:
      self._successes += 1

      if reply.attribute(QNetworkRequest.SourceIsFromCacheAttribute):
        self._cacheHits += 1

      elif not reply.hasRawHeader(b"Cache-Control"):
        cache = QgsNetworkAccessManager.instance().cache()
        if cache:
          metadata = cache.metaData(reply.request().url())
          if metadata.expirationDate().isNull():
            metadata.setExpirationDate(QDateTime.currentDateTime().addSecs(self.defaultCacheExpiration * 3600))
            cache.updateMetaData(metadata)
            self.log("Default expiration date has been set: %s (%d h)" % (url, self.defaultCacheExpiration))

      if reply.isReadable():
        data = reply.readAll()
        self.fetchedFiles[url] = data
      else:
        qDebug("http status code: " + str(httpStatusCode))

    else:
      self._errors += 1
      if self.errorStatus == self.NO_ERROR:
        self.errorStatus = self.UNKNOWN_ERROR

    self.replyFinished.emit(url)
    reply.deleteLater()

    if len(self.queue) + len(self.requestingReplies) == 0:
      # all replies have been received
      if self.sync:
        self.logT("eventLoop.quit()")
        self.eventLoop.quit()
      else:
        self.timer.stop()

      self.allRepliesFinished.emit()

    elif len(self.queue) > 0:
      # start fetching the next file
      self.fetchNext()

  def timeOut(self):
    self.log("Downloader.timeOut()")
    self.abort()
    self.errorStatus = Downloader.TIMEOUT_ERROR

  @pyqtSlot()
  def abort(self, stopTimer=True):
    # clear queue and abort requests
    self.queue = []

    for reply in self.requestingReplies.values():
      url = reply.url().toString()
      reply.abort()
      reply.deleteLater()
      self.log("request aborted: {0}".format(url))

    self.errorStatus = Downloader.UNKNOWN_ERROR
    self.requestingReplies = {}

    if stopTimer:
      self.timer.stop()

  def fetchNext(self):
    if len(self.queue) == 0:
      return
    url = self.queue.pop(0)
    self.log("fetchNext: %s" % url)

    # create request
    request = QNetworkRequest(QUrl(url))
    if self.userAgent:
      request.setRawHeader(b"User-Agent", self.userAgent.encode("ascii", "ignore"))    # will be overwritten in QgsNetworkAccessManager::createRequest() since 2.2

    # send request
    reply = QgsNetworkAccessManager.instance().get(request)
    reply.finished.connect(self._replyFinished)
    self.requestingReplies[url] = reply
    return reply

  def fetchFiles(self, urlList, timeoutSec=0):
    self.log("fetchFiles()")
    files = self._fetch(True, urlList, timeoutSec)
    self.log("fetchFiles() End: %d" % self.errorStatus)
    return files

  @pyqtSlot(list, int)
  def fetchFilesAsync(self, urlList, timeoutSec=0):
    self.log("fetchFilesAsync()")
    self._fetch(False, urlList, timeoutSec)

  def _fetch(self, sync, urlList, timeoutSec):
    self.clear()
    self.sync = sync

    if not urlList:
      return {}

    for url in urlList:
      if url not in self.queue:
        self.queue.append(url)

    for i in range(self.maxConnections):
      self.fetchNext()

    if timeoutSec > 0:
      self.timer.setInterval(timeoutSec * 1000)
      self.timer.start()

    if sync:
      self.logT("eventLoop.exec_(): " + str(self.eventLoop))
      self.eventLoop.exec_()

      if timeoutSec > 0:
        self.timer.stop()

      return self.fetchedFiles

  def log(self, msg):
    if DEBUG_MODE:
      qDebug(msg)

  def logT(self, msg):
    if DEBUG_MODE:
      qDebug("%s: %s" % (str(threading.current_thread()), msg))

  def finishedCount(self):
    return len(self.fetchedFiles)

  def unfinishedCount(self):
    return len(self.queue) + len(self.requestingReplies)

  def stats(self):
    finished = self.finishedCount()
    unfinished = self.unfinishedCount()
    return {"total": finished + unfinished,
            "finished": finished,
            "unfinished": unfinished,
            "successed": self._successes,
            "errors": self._errors,
            "cacheHits": self._cacheHits,
            "downloaded": self._successes - self._cacheHits}
