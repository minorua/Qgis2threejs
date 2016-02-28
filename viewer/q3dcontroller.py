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
import os
from PyQt4.QtCore import Qt, QBuffer, QByteArray, QIODevice, QObject, pyqtSignal
from PyQt4.QtGui import QDialog, QDialogButtonBox
from qgis.core import QGis, QgsMapLayer, QgsMapLayerRegistry

import q3dconst
from socketserver import SocketServer
from Qgis2threejs.exportsettings import ExportSettings
from Qgis2threejs.propertypages import DEMPropertyPage, VectorPropertyPage
from Qgis2threejs.qgis2threejscore import MapTo3D
from Qgis2threejs.qgis2threejsdialog import RectangleMapTool
from Qgis2threejs.qgis2threejstools import logMessage
from Qgis2threejs.writer import ThreejsJSWriter, writeSimpleDEM, writeVector    #writeMultiResDEM
from ui.propertiesdialog import Ui_PropertiesDialog


class Q3DController:

  def __init__(self, qgis_iface, objectTypeManager, pluginManager, serverName="Qgis2threejs"):
    self.qgis_iface = qgis_iface
    self.objectTypeManager = objectTypeManager
    self.pluginManager = pluginManager
    self.requestQueue = []
    self._processing = False

    self.iface = SocketServer(serverName, qgis_iface.mainWindow())
    self.iface.log = logMessage   # override
    self.iface.notified.connect(self.notified)
    self.iface.requestReceived.connect(self.requestReceived)
    self.iface.responseReceived.connect(self.responseReceived)

    qgis_iface.mapCanvas().renderComplete.connect(self.canvasUpdated)
    qgis_iface.mapCanvas().extentsChanged.connect(self.canvasExtentChanged)

    defaultSettings = json.loads('{"DEM":{"checkBox_Clip":false,"checkBox_Frame":false,"checkBox_Shading":true,"checkBox_Sides":true,"checkBox_Surroundings":false,"checkBox_TransparentBackground":false,"comboBox_ClipLayer":null,"comboBox_DEMLayer":"plugin:gsielevtile","comboBox_TextureSize":100,"horizontalSlider_DEMSize":2,"lineEdit_Color":"","lineEdit_ImageFile":"","lineEdit_centerX":"","lineEdit_centerY":"","lineEdit_rectHeight":"","lineEdit_rectWidth":"","radioButton_MapCanvas":true,"radioButton_Simple":true,"spinBox_Height":4,"spinBox_Roughening":4,"spinBox_Size":5,"spinBox_demtransp":0,"visible":false},"OutputFilename":"","PluginVersion":"1.4","Template":"3DViewer(dat-gui).html"}')

    exportSettings = ExportSettings(pluginManager, True)
    exportSettings.loadSettings(defaultSettings)
    exportSettings.setMapCanvas(qgis_iface.mapCanvas())

    err_msg = exportSettings.checkValidity()
    if err_msg is not None:
      logMessage(err_msg or "Invalid settings")
      return
    self.exportSettings = exportSettings
    self.writer = ThreejsJSWriter(None, exportSettings, objectTypeManager)   #multiple_files=bool(settings.exportMode == ExportSettings.PLAIN_MULTI_RES))

  def canvasUpdated(self, painter):
    self.iface.notify(q3dconst.N_CANVAS_IMAGE_UPDATED)
    logMessage("N_CANVAS_IMAGE_UPDATED notification sent")

  def canvasExtentChanged(self):
    self.iface.notify(q3dconst.N_CANVAS_EXTENT_CHANGED)
    logMessage("N_CANVAS_EXTENT_CHANGED notification sent")

  def notified(self, code, params):
    if code == q3dconst.N_LAYER_DOUBLECLICKED:
      self.showPropertiesDialog(params["id"], params["layerId"], params["properties"])

  def requestReceived(self, dataType, params):
    #TODO: remove any duplicate requests in requestQueue if the request is sent to update 3d model (e.g. JS_UPDATE_LAYER).
    self.requestQueue.append([dataType, params])
    if not self._processing:
      self.processNextRequest()

  def responseReceived(self, data, dataType):
    pass

  def processNextRequest(self):
    if self._processing or len(self.requestQueue) == 0:
      return
    self._processing = True
    dataType, params = self.requestQueue.pop(0)

    if dataType in [q3dconst.JS_CREATE_LAYER, q3dconst.JS_UPDATE_LAYER]:
      self.exportSettings.setMapCanvas(self.qgis_iface.mapCanvas())

      ba = QByteArray()
      buf = QBuffer(ba)
      buf.open(QIODevice.ReadWrite)
      self.writer.setDevice(buf)

      geomType = params["geomType"]
      properties = params["properties"]
      properties["comboBox_DEMLayer"] = params["layerId"]

      if dataType == q3dconst.JS_CREATE_LAYER:
        if geomType == q3dconst.TYPE_DEM:
          writeSimpleDEM(self.writer, properties)
          self.writer.writeImages()
        elif geomType == q3dconst.TYPE_IMAGE:
          pass
        else:
          writeVector(self.writer, params["layerId"], properties)

        buf.write("""
lyr.pyLayerIndex = {0};
pyObj.setLayerId({0}, lyr.index);

lyr.initMaterials();
lyr.build(app.scene);
lyr.objectGroup.updateMatrixWorld();
app.queryObjNeedsUpdate = true;
if (!app.running) app.start();
""".format(params["id"]))

      else:   # q3dconst.JS_UPDATE_LAYER
        buf.write("lyr = undefined;\n")
        if geomType == q3dconst.TYPE_DEM:
          writeSimpleDEM(self.writer, properties)   #TODO: option to use setLayer() instead of addLayer()
          self.writer.writeImages()
        #elif geomType == q3dconst.TYPE_IMAGE:
        #  pass
        else:
          writeVector(self.writer, params["layerId"], properties)   #TODO: option to use setLayer() instead of addLayer()

        buf.write("""
lyr.initMaterials();
lyr.build(app.scene);
lyr.objectGroup.updateMatrixWorld();
app.queryObjNeedsUpdate = true;
""")
        ba = ba.replace("lyr = project.addLayer(", "lyr = project.setLayer({0}, ".format(params["jsLayerId"]))

      self.iface.respond(ba, dataType)   # q3dconst.FORMAT_JS

    elif dataType in [q3dconst.JS_CREATE_PROJECT, q3dconst.JS_UPDATE_PROJECT]:
      self.exportSettings.setMapCanvas(self.qgis_iface.mapCanvas())

      ba = QByteArray()
      buf = QBuffer(ba)
      buf.open(QIODevice.ReadWrite)
      self.writer.setDevice(buf)
      self.writer.writeProject()

      if dataType == q3dconst.JS_CREATE_PROJECT:
        buf.write("app.loadProject(project);")
      else:
        ba = ba.replace("project = new Q3D.Project", "project.update")
      self.iface.respond(ba, dataType)   # q3dconst.FORMAT_JS

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

      self.iface.respond(QByteArray(json.dumps(layers)), dataType)    # q3dconst.FORMAT_JSON

    elif dataType == q3dconst.BIN_CANVAS_IMAGE:
      ba = QByteArray()
      buf = QBuffer(ba)
      buf.open(QIODevice.ReadWrite)
      self.qgis_iface.mapCanvas().map().contentImage().save(buf, "PNG")
      #TODO: image.bits()?
      self.iface.respond(ba, dataType)    # q3dconst.FORMAT_BINARY

    self._processing = False
    self.processNextRequest()

  def showPropertiesDialog(self, id, layerId, geomType, properties=None):
    layer = QgsMapLayerRegistry.instance().mapLayer(unicode(layerId))
    if layer is None:
      return

    properties = properties or {}
    dialog = PropertiesDialog(self.qgis_iface, self.objectTypeManager, self.pluginManager)
    dialog.setLayer(id, layer, geomType, properties)
    dialog.show()
    dialog.propertiesChanged.connect(self.propertiesChanged)
    dialog.exec_()

  def propertiesChanged(self, id, properties):
    self.iface.notify(q3dconst.N_LAYER_PROPERTIES_CHANGED, {"id": id, "properties": properties})


class PropertiesDialog(QDialog):

  propertiesChanged = pyqtSignal(int, dict)

  def __init__(self, iface, objectTypeManager, pluginManager):
    QDialog.__init__(self, iface.mainWindow())
    self.iface = iface
    self.objectTypeManager = objectTypeManager
    self.pluginManager = pluginManager

    # Set up the user interface from Designer.
    self.ui = Ui_PropertiesDialog()
    self.ui.setupUi(self)
    self.ui.buttonBox.clicked.connect(self.buttonClicked)

    self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
    self.activateWindow()

  def setLayer(self, id, layer, geomType, properties):
    self.layerId = id
    self.layer = layer
    self.geomType = geomType
    self.properties = properties or {}

    self.setWindowTitle(u"Layer Properties - {0} (Qgis2threejs)".format(layer.name()))

    dialog = MockDialog(self.iface, self.objectTypeManager, self.pluginManager, self)
    if geomType == q3dconst.TYPE_DEM:
      self.page = DEMPropertyPage(dialog)
      self.page.setup(properties, layer, False)
    elif geomType == q3dconst.TYPE_IMAGE:
      return
    else:
      self.page = VectorPropertyPage(dialog)
      self.page.setup(properties, layer)
    self.ui.scrollArea.setWidget(self.page)

  def buttonClicked(self, button):
    role = self.ui.buttonBox.buttonRole(button)
    if role in [QDialogButtonBox.AcceptRole, QDialogButtonBox.ApplyRole]:
      self.propertiesChanged.emit(self.layerId, self.page.properties())
      self.setWindowTitle("buttonClicked: {0}".format(role))


class MockTreeWidgetItem:

  def data(self, i, j):
    return Qt.Checked


class MockDialog(QObject):

  def __init__(self, iface, objectTypeManager, pluginManager, parent=None):
    QObject.__init__(self, parent)
    self.iface = iface
    self.objectTypeManager = objectTypeManager
    self.pluginManager = pluginManager

    self.currentItem = MockTreeWidgetItem()
    self.mapTool = RectangleMapTool(iface.mapCanvas())

  def mapTo3d(self):
    canvas = self.iface.mapCanvas()
    mapSettings = canvas.mapSettings() if QGis.QGIS_VERSION_INT >= 20300 else canvas.mapRenderer()

    #world = self._settings.get(ObjectTreeItem.ITEM_WORLD, {})
    #bs = float(world.get("lineEdit_BaseSize", def_vals.baseSize))
    #ve = float(world.get("lineEdit_zFactor", def_vals.zExaggeration))
    #vs = float(world.get("lineEdit_zShift", def_vals.zShift))

    return MapTo3D(mapSettings, 100, 1.5, 0)

  def setWindowState(self, state):
    pass

  def startPointSelection(self):
    pass

  def endPointSelection(self):
    pass

  def createRubberBands(self, baseExtent, quadtree):
    pass

  def clearRubberBands(self):
    pass

  def primaryDEMChanged(self, layerId):
    pass
