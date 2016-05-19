# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DController

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
import json
import time
from PyQt4.QtCore import QBuffer, QByteArray, QIODevice, QObject, QThread, pyqtSignal
from qgis.core import QGis, QgsMapLayer, QgsMessageLog

from . import q3dconst
from .socketserver import SocketServer
from Qgis2threejs.exportsettings import ExportSettings
from Qgis2threejs.writer import ThreejsJSWriter, writeSimpleDEM, writeVector    #writeMultiResDEM
from Qgis2threejs.qgis2threejstools import pyobj2js

def logMessage(message):
  try:
    QgsMessageLog.logMessage(str(message), "Qgis2threejs")
  except:
    pass


class Buffer:

  def __init__(self):
    self.data = QByteArray()
    self.buf = QBuffer(self.data)
    self.buf.open(QIODevice.ReadWrite)
    self.write = self.buf.write


class LiveThreejsJSWriter(ThreejsJSWriter):

  dataReady = pyqtSignal("QByteArray")

  def __init__(self, settings, objectTypeManager, parent=None):
    ThreejsJSWriter.__init__(self, None, settings, objectTypeManager, parent)
    self.write = self._write
    self.clearBuffer()

    self.layer = None
    self.jsLayerId = None

    self.writtenTick = 0
    self.writtenTime = None

  def clearBuffer(self):
    self.buf = Buffer()

  def _write(self, data):
    self.buf.write(data)
    self.writtenTick += 1

    if self.writtenTime is None:
      self.writtenTime = time.time()

    elif self.writtenTick > 10:
      if time.time() - self.writtenTime > 2:    # 2 secs
        self.flush()
      else:
        self.writtenTick = 0

  def flush(self):
    if self.buf.data.size() > 0:
      self.dataReady.emit(self.buf.data)
      self.clearBuffer()

    self.writtenTick = 0
    self.writtenTime = None

  def createProject(self, _params):
    self.writeProject()
    self.buf.write("app.loadProject(project);")
    self.flush()

  def updateProject(self, _params):
    self.writeProject(update=True)
    self.flush()

  def createLayer(self, params):
    self._writeLayer(params["layer"])
    self.flush()

  def updateLayer(self, params):
    self.isCanceled = False
    self.buf.write("lyr = undefined;\n")
    layer = params["layer"]
    self._writeLayer(layer, layer["jsLayerId"])
    self.flush()

  def _writeLayer(self, params, jsLayerId=None):
    self.jsLayerId = jsLayerId

    geomType = params["geomType"]
    properties = params["properties"]
    if geomType == q3dconst.TYPE_DEM:
      properties["comboBox_DEMLayer"] = params["layerId"]
      writeSimpleDEM(self, properties)
      self.writeImages()
      self.buf.write("""
lyr.initMaterials();
lyr.build(app.scene);
lyr.objectGroup.updateMatrixWorld();
""")
    # elif geomType == q3dconst.TYPE_IMAGE:
    #  pass
    else:
      writeVector(self, params["layerId"], properties, noFeature=(jsLayerId is None))

    if jsLayerId is None:
      self.buf.write("""
lyr.pyLayerIndex = {0};
pyObj.setLayerId({0}, lyr.index);
""".format(params["id"]))

    self.buf.write("""
app.queryObjNeedsUpdate = true;
""")

  def writeLayer(self, layer, fieldNames=None, jsLayerId=None):
    # pass self.jsLayerId
    self.layer = layer
    return ThreejsJSWriter.writeLayer(self, layer, fieldNames, self.jsLayerId)

  def writeFeature(self, f):
    if self.jsLayerId is None:
      self.write("// LiveThreejsJSWriter: feature not written because jsLayerId is None. # TODO\n")
    else:
      manager = self.layer.materialManager
      writtenCount = manager.writtenCount
      manager.write(self, self.imageManager)
      if manager.writtenCount > writtenCount:
        self.write("createMaterials({0});\n".format(self.jsLayerId))

      #TODO: self.imageManager.write(self)

      self.currentFeatureIndex += 1
      self.write("addFeat({0}, {1}); //{2}\n".format(self.jsLayerId, pyobj2js(f), self.currentFeatureIndex))


class Worker(QObject):

  # signals
  startJob = pyqtSignal(int, dict)                    # jobId, kargs
  jobFinished = pyqtSignal(int, dict)                 # jodId, kargs
  jobCancelled = pyqtSignal(int, dict)                # jodId, kargs
  dataReady = pyqtSignal(int, "QByteArray", dict)     # jodId, data, kargs

  def __init__(self):
    QObject.__init__(self)
    self.isActive = False
    self.isCanceled = False
    self.jobId = -1
    self.kargs = {}

  def startJobSlot(self, jobId, kargs):
    self.jobId = jobId
    self.kargs = kargs
    self.isActive = True
    self.isCanceled = False

    self.run(kargs)

    self.jobId = -1
    self.isActive = False
    if self.isCanceled:
      self.jobCancelled.emit(jobId, kargs)
    else:
      self.jobFinished.emit(jobId, kargs)

  def cancelJob(self):
    self.isCanceled = True

  # should be overridden
  def run(self, kargs):
    pass


class Writer(Worker):

  def __init__(self, parent):
    Worker.__init__(self)

    self._parent = parent
    self.qgis_iface = parent.qgis_iface
    self.pluginManager = parent.pluginManager

    # writing machine
    self.writer = LiveThreejsJSWriter(parent.exportSettings, parent.objectTypeManager, self)
    self.writer.dataReady.connect(self.writerDataReady)

  def writerDataReady(self, data):
    self.dataReady.emit(self.jobId, data, self.kargs)

  def cancelJob(self):
    self.writer.isCanceled = True
    self.isCanceled = True

  def run(self, params):
    dataType = params["dataType"]
    func = {q3dconst.JS_CREATE_LAYER: self.writer.createLayer,
            q3dconst.JS_UPDATE_LAYER: self.writer.updateLayer,
            q3dconst.JS_CREATE_PROJECT: self.writer.createProject,
            q3dconst.JS_UPDATE_PROJECT: self.writer.updateProject}.get(dataType)

    if func:
      func(params)
      return

    if dataType == q3dconst.JS_SAVE_IMAGE:
      js = "saveCanvasImage({0}, {1});".format(params["width"], params["height"])
      data = QByteArray(js)

    elif dataType == q3dconst.JS_START_APP:
      js = "if (!app.running) app.start();"
      data = QByteArray(js)

    elif dataType == q3dconst.JSON_LAYER_LIST:
      layers = []
      for plugin in self.pluginManager.demProviderPlugins():
        layers.append({"layerId": "plugin:" + plugin.providerId(), "name": plugin.providerName(), "geomType": q3dconst.TYPE_DEM})

      for layer in self.qgis_iface.legendInterface().layers():
        layerType = layer.type()
        if layerType == QgsMapLayer.VectorLayer:
          geomType = {QGis.Point: q3dconst.TYPE_POINT,
                      QGis.Line: q3dconst.TYPE_LINESTRING,
                      QGis.Polygon: q3dconst.TYPE_POLYGON,
                      QGis.UnknownGeometry: None,
                      QGis.NoGeometry: None}[layer.geometryType()]
        elif layerType == QgsMapLayer.RasterLayer and layer.providerType() == "gdal" and layer.bandCount() == 1:
          geomType = q3dconst.TYPE_DEM
        else:
          geomType = q3dconst.TYPE_IMAGE
          continue

        if geomType is not None:
          layers.append({"layerId": layer.id(), "name": layer.name(), "geomType": geomType})

      data = QByteArray(json.dumps(layers))       # q3dconst.FORMAT_JSON

    else:
      data = QByteArray()

    self.dataReady.emit(self.jobId, data, params)


class WorkerManager(QObject):

  def __init__(self, maxWorkerCount=1, parent=None):
    QObject.__init__(self, parent)

    self.workers = []
    self.threads = []
    self.requestQueue = []

    self.maxWorkerCount = maxWorkerCount
    self.activeWorkerCount = 0
    self.isWorkingExclusively = False

    self.lastJobId = 0

  # should be overridden
  def createWorker(self):
    return None

  def availableWorker(self):
    workerCount = self.workerCount()
    if self.activeWorkerCount < workerCount:
      for worker in self.workers:
        if not worker.isActive:
          return worker

    if workerCount >= self.maxWorkerCount:
      return None

    worker = self.createWorker()
    if worker is None:
      return None

    assert worker.parent() is None

    thread = QThread(self)
    worker.moveToThread(thread)
    worker.startJob.connect(worker.startJobSlot)
    worker.jobFinished.connect(self.jobFinished)
    worker.jobCancelled.connect(self.jobCanceled)
    worker.dataReady.connect(self.dataReady)
    thread.finished.connect(worker.deleteLater)
    thread.start()

    self.workers.append(worker)
    self.threads.append(thread)
    return worker

  def workerCount(self):
    return len(self.workers)

  def nextJobId(self):
    self.lastJobId += 1
    return self.lastJobId

  def jobFinished(self, jobId, kargs):
    self.activeWorkerCount -= 1
    if self.isWorkingExclusively:
      assert self.activeWorkerCount == 0
    self.isWorkingExclusively = False
    self.processNextRequest()

  def jobCanceled(self, jobId, kargs):
    logMessage("jobCanceled: {0} ({1})".format(jobId, str(kargs)))
    self.jobFinished(jobId, kargs)

  # should be overridden
  def dataReady(self, jobId, data, meta):
    pass

  def request(self, params, exclusive=False):
    jobId = self.nextJobId()
    self.requestQueue.append([jobId, params, exclusive])
    self.processNextRequest()
    return jobId
    #TODO: remove any duplicate requests in requestQueue if the request is sent to update 3d model (e.g. JS_UPDATE_LAYER).

  def processNextRequest(self, _jobId=-1):
    if len(self.requestQueue) == 0 or self.isWorkingExclusively:
      return

    jobId, params, exclusive = self.requestQueue[0]
    if exclusive and self.activeWorkerCount > 0:
      return

    worker = self.availableWorker()
    if worker is None:
      return

    self.requestQueue.pop(0)
    self.activeWorkerCount += 1
    if exclusive:
      self.isWorkingExclusively = True

    # start job!
    params["exclusive"] = exclusive
    worker.startJob.emit(jobId, params)

  def cancelJobs(self):
    for worker in self.workers:
      if worker.isActive:
        worker.cancelJob()


class Q3DController(WorkerManager):

  #TODO: parent
  def __init__(self, qgis_iface, objectTypeManager, pluginManager, serverName, parent=None):
    WorkerManager.__init__(self, 1, parent)

    defaultSettings = json.loads('{"DEM":{"checkBox_Clip":false,"checkBox_Frame":false,"checkBox_Shading":true,"checkBox_Sides":true,"checkBox_Surroundings":false,"checkBox_TransparentBackground":false,"comboBox_ClipLayer":null,"comboBox_DEMLayer":"plugin:gsielevtile","comboBox_TextureSize":100,"horizontalSlider_DEMSize":2,"lineEdit_Color":"","lineEdit_ImageFile":"","lineEdit_centerX":"","lineEdit_centerY":"","lineEdit_rectHeight":"","lineEdit_rectWidth":"","radioButton_MapCanvas":true,"radioButton_Simple":true,"spinBox_Height":4,"spinBox_Roughening":4,"spinBox_Size":5,"spinBox_demtransp":0,"visible":false},"OutputFilename":"","PluginVersion":"1.4","Template":"3DViewer(dat-gui).html"}')

    exportSettings = ExportSettings(pluginManager, True)
    exportSettings.loadSettings(defaultSettings)
    exportSettings.setMapCanvas(qgis_iface.mapCanvas())

    err_msg = exportSettings.checkValidity()
    if err_msg is not None:
      logMessage(err_msg or "Invalid settings")
      return

    self.qgis_iface = qgis_iface
    self.objectTypeManager = objectTypeManager
    self.pluginManager = pluginManager
    self.exportSettings = exportSettings

    self.iface = SocketServer(serverName, qgis_iface.mainWindow())
    self.iface.log = logMessage   # override
    self.iface.notified.connect(self.notified)
    self.iface.requestReceived.connect(self.requestReceived)
    self.iface.responseReceived.connect(self.responseReceived)

  def createWorker(self):
    return Writer(self)

  def cancelJobs(self, renderId=None):
    logMessage("cancelJobs: renderId={0}".format(renderId))
    for worker in self.workers:
      if worker.isActive:   #TODO: renderId is None or worker.renderId == renderId
        worker.cancelJob()

  def dataReady(self, jobId, data, meta):
    self.iface.respond(data, meta)

  def notified(self, params):
    if params.get("code") == q3dconst.N_LAYER_DOUBLECLICKED:
      self.showPropertiesDialog(params["id"], params["layerId"], params["properties"])

  def requestReceived(self, params):
    exclusive = False if params["dataType"] == q3dconst.JS_UPDATE_LAYER else True
    self.request(params, exclusive)

  def responseReceived(self, data, meta):
    pass


def processRequest(worker, dataType, params):
  qgis_iface = worker.qgis_iface
  pluginManager = worker.pluginManager
  writer = worker.writer

  if dataType == q3dconst.BIN_CANVAS_IMAGE:
    buf = Buffer()
    qgis_iface.mapCanvas().map().contentImage().save(buf, "PNG")
    #TODO: image.bits()?
    return buf.data       # q3dconst.FORMAT_BINARY

  return QByteArray()
