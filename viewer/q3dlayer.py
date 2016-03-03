# -*- coding: utf-8 -*-
"""
/***************************************************************************
  Qgis2threejsLayer
                              -------------------
        begin                : 2016-02-28
        copyright            : (C) 2016 by Minoru Akagi
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
import os
import threading

from PyQt4.QtCore import QByteArray, QEventLoop, QFile, QObject, QTimer, QProcess, pyqtSignal, qDebug
from PyQt4.QtGui import QImage, QPainter
from qgis.core import QGis, QgsMapLayer, QgsMapLayerRegistry, QgsPluginLayer, QgsPluginLayerType, QgsMessageLog
from qgis.gui import QgsMessageBar

import q3dconst
from q3dcontroller import Q3DController
from Qgis2threejs.rotatedrect import RotatedRect

debug_mode = 1


def logMessage(message):
  try:
    QgsMessageLog.logMessage(unicode(message), "Qgis2threejs")
  except:
    pass


class Q3DLayerController(Q3DController):

  renderCompleted = pyqtSignal()

  def __init__(self, qgis_iface, objectTypeManager, pluginManager, serverName):
    Q3DController.__init__(self, qgis_iface, objectTypeManager, pluginManager, serverName)
    self.renderedImage = None
    self.layers = []

  def setLayers(self, layers):
    self.layers = layers

  def responseReceived(self, data, dataType):
    if dataType == q3dconst.BIN_SCENE_IMAGE:
      self.renderedImage = QImage()
      self.renderedImage.loadFromData(data)
      self.renderCompleted.emit()

    else:
      Q3DController.responseReceived(self, data, dataType)

  def processRequest(self, dataType, params):
    if dataType == q3dconst.JSON_LAYER_LIST:
      layers = []
      for layer in self.layers:
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
          properties = json.loads(q3dconst.DEFAULT_PROPERTIES[geomType])

          if geomType == q3dconst.TYPE_POLYGON:
            properties["checkBox_Clip"] = False
            properties["heightWidget"]["comboData"] = 1
            properties["heightWidget"]["editText"] = "0"

            fnIdx = layer.fields().fieldNameIndex("height")
            if fnIdx != -1:   # if layer has height attribute
              properties["styleWidget2"]["comboData"] = 100 + fnIdx   # FIRST_ATTRIBUTE = 100
              properties["styleWidget2"]["comboText"] = '"height"'
              properties["styleWidget2"]["editText"] = "1"

          layers.append({"layerId": layer.id(),
                         "name": layer.name(),
                         "geomType": geomType,
                         "visible": True,
                         "properties": properties})

      self.iface.respond(QByteArray(json.dumps(layers)), dataType)    # q3dconst.FORMAT_JSON
      self.qgis_iface.mapCanvas().refresh()

    else:
      Q3DController.processRequest(self, dataType, params)


class Qgis2threejsRenderer(QObject):

  renderCompleted = pyqtSignal()

  def renderedImage(self):
    return self.controller.renderedImage

  def clearImage(self):
    self.controller.renderedImage = None


class Qgis2threejs25DRenderer(Qgis2threejsRenderer):

  def setup(self, layer, serverName):
    self.layer = layer
    self.controller = Q3DLayerController(layer.iface, layer.objectTypeManager, layer.pluginManager, serverName)
    self.controller.renderCompleted.connect(self.renderCompleted)

  def setLayers(self, layers):
    self.controller.setLayers(layers)

  def render(self, renderContext):
    logMessage("Qgis2threejs25DRenderer.render()")
    extent = renderContext.extent()
    if extent.isEmpty() or extent.width() == float("inf"):
      qDebug("Drawing is skipped because map extent is empty or inf.")
      return True

    map2pixel = renderContext.mapToPixel()
    mupp = map2pixel.mapUnitsPerPixel()
    painter = renderContext.painter()
    viewport = painter.viewport()
    rotation = map2pixel.mapRotation()    # if self.plugin.apiChanged27 else 0
    mapExtent = RotatedRect(extent.center(), mupp * viewport.width(), mupp * viewport.height(), rotation)
    rect = mapExtent.unrotatedRect()

    #self.controller.exportSettings.baseExtent = mapExtent    #
    params = {
      "width": viewport.width(),
      "height": viewport.height(),
      "baseExtent": [rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()],
      "rotation": rotation
    }
    self.controller.iface.request(q3dconst.BIN_SCENE_IMAGE, params)


class Qgis2threejs3DRenderer(Qgis2threejsRenderer):
  pass


class Qgis2threejsLayer(QgsPluginLayer):

  LAYER_TYPE = "Qgis2threejsLayer"
  DEFAULT_BLEND_MODE = "SourceOver"
  DEFAULT_SMOOTH_RENDER = True

  # signals
  statusSignal = pyqtSignal(str, int)
  messageBarSignal = pyqtSignal(str, str, int, int)

  def __init__(self, plugin, serverName="Qgis2threejs"):
    layer = plugin.iface.activeLayer()
    title = "[2.5D] " + layer.name() if layer else ""
    QgsPluginLayer.__init__(self, Qgis2threejsLayer.LAYER_TYPE, title)
    if layer is None:
      return
    self.setValid(True)

    self.plugin = plugin
    self.iface = plugin.iface
    self.objectTypeManager = plugin.objectTypeManager
    self.pluginManager = plugin.pluginManager

    self.renderer = Qgis2threejs25DRenderer()   #self.id())
    self.renderer.setup(self, serverName)
    self.renderer.setLayers([self.iface.activeLayer()])

    # set custom properties
    #self.setCustomProperty("title", title)

    # set extent
    #self.setExtent(QgsRectangle(-layerDef.TSIZE1, -layerDef.TSIZE1, layerDef.TSIZE1, layerDef.TSIZE1))

    # set styles
    self.setTransparency(0)
    self.setBlendModeByName(self.DEFAULT_BLEND_MODE)
    self.setSmoothRender(self.DEFAULT_SMOOTH_RENDER)

    # multi-thread
    if self.iface:
      self.statusSignal.connect(self.showStatusMessageSlot)
      self.messageBarSignal.connect(self.showMessageBarSlot)

    logMessage("Launching Qgis2threejs Renderer...")
    this_dir = os.path.dirname(QFile.decodeName(__file__))
    parent = self.iface.mainWindow()
    p = QProcess(parent)
    if os.name == "nt":
      os.system("start cmd.exe /c {0} -r -n {1}".format(os.path.join(this_dir, "q3drenderer.bat"), serverName))
      return
      cmd = r"C:\Python34\python.exe"
    else:
      cmd = "python3"
    p.start(cmd, [os.path.join(this_dir, "q3dapplication.py"), "-r", "-n", serverName])

    if not p.waitForStarted():
      logMessage("Cannot launch Qgis2threejs Renderer (code: {0}).".format(p.error()))

  def setBlendModeByName(self, modeName):
    self.blendModeName = modeName
    blendMode = getattr(QPainter, "CompositionMode_" + modeName, 0)
    self.setBlendMode(blendMode)
    self.setCustomProperty("blendMode", modeName)

  def setTransparency(self, transparency):
    self.transparency = transparency
    self.setCustomProperty("transparency", transparency)

  def setSmoothRender(self, isSmooth):
    self.smoothRender = isSmooth
    self.setCustomProperty("smoothRender", 1 if isSmooth else 0)

  def draw(self, renderContext):
    self.logT("Qgis2threejsLayer.draw")

    # create a QEventLoop object that belongs to the current worker thread
    eventLoop = QEventLoop()
    self.renderer.renderCompleted.connect(eventLoop.quit)
    self.renderer.clearImage()
    self.renderer.render(renderContext)

    # create a timer to watch whether rendering is stopped
    watchTimer = QTimer()
    watchTimer.timeout.connect(eventLoop.quit)

    # wait for the fetch to finish
    timeout = 30
    tick = 0
    interval = 500
    timeoutTick = timeout * 1000 / interval
    watchTimer.start(interval)
    while tick < timeoutTick:
      # run event loop for 0.5 seconds at maximum
      eventLoop.exec_()
      # break if rendering has been finished
      if self.renderer.renderedImage() or renderContext.renderingStopped():   #TODO: isRendered
        break
      tick += 1
    watchTimer.stop()

    image = self.renderer.renderedImage()
    if image is None:
      return True

    painter = renderContext.painter()
    #viewport = painter.viewport()
    #painter.eraseRect(QRect(0, 0, viewport.width(), viewport.height()))
    painter.drawImage(0, 0, image)
    painter.drawText(0, 10, "Qgis2threejs")
    return True

  def readXml(self, node):
    self.readCustomProperties(node)
    #title = self.customProperty("title", "")

    # layer style
    self.setTransparency(int(self.customProperty("transparency", 0)))
    self.setBlendModeByName(self.customProperty("blendMode", self.DEFAULT_BLEND_MODE))
    self.setSmoothRender(int(self.customProperty("smoothRender", self.DEFAULT_SMOOTH_RENDER)))
    return True

  def writeXml(self, node, doc):
    element = node.toElement();
    element.setAttribute("type", "plugin")
    element.setAttribute("name", Qgis2threejsLayer.LAYER_TYPE);
    return True

  def readSymbology(self, node, errorMessage):
    return False

  def writeSymbology(self, node, doc, errorMessage):
    return False

  def metadata(self):
    lines = []
    fmt = u"%s:\t%s"
    lines.append(fmt % (self.tr("Title"), "title"))
    return "\n".join(lines)

  def showStatusMessage(self, msg, timeout=0):
    self.statusSignal.emit(msg, timeout)

  def showStatusMessageSlot(self, msg, timeout):
    self.iface.mainWindow().statusBar().showMessage(msg, timeout)

  def showMessageBar(self, text, level=QgsMessageBar.INFO, duration=0, title=None):
    if title is None:
      title = self.plugin.pluginName
    self.messageBarSignal.emit(title, text, level, duration)

  def showMessageBarSlot(self, title, text, level, duration):
    self.iface.messageBar().pushMessage(title, text, level, duration)

  def log(self, msg):
    if debug_mode:
      qDebug(msg)

  def logT(self, msg):
    if debug_mode:
      qDebug("%s: %s" % (str(threading.current_thread()), msg))

  def dump(self, detail=False, bbox=None):
    pass

#  def createMapRenderer(self, renderContext):
#    qDebug("createMapRenderer")
#    self.renderer = QgsPluginLayerRenderer(self, renderContext)
#    return self.renderer


class Qgis2threejs25DLayerType(QgsPluginLayerType):
  def __init__(self, plugin):
    QgsPluginLayerType.__init__(self, Qgis2threejsLayer.LAYER_TYPE)
    self.plugin = plugin

  def createLayer(self):
    return Qgis2threejs25DLayerType(self.plugin)

  def showLayerProperties(self, layer):
    return True
    """
    from propertiesdialog import PropertiesDialog
    dialog = PropertiesDialog(layer)
    dialog.applyClicked.connect(self.applyClicked)
    dialog.show()
    accepted = dialog.exec_()
    if accepted:
      self.applyProperties(dialog)
    return True
    """

  def applyClicked(self):
    self.applyProperties(QObject().sender())

  def applyProperties(self, dialog):
    layer = dialog.layer
    layer.setTransparency(dialog.ui.spinBox_Transparency.value())
    layer.setBlendModeByName(dialog.ui.comboBox_BlendingMode.currentText())
    layer.setSmoothRender(dialog.ui.checkBox_SmoothRender.isChecked())
    layer.setCreditVisibility(dialog.ui.checkBox_CreditVisibility.isChecked())
    layer.repaintRequested.emit()
