# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DControllerLive

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
from qgis.PyQt.QtCore import Qt, QObject, pyqtSignal
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox
from qgis.core import QGis, QgsMapLayerRegistry

from . import q3dconst
from .q3dcontroller import Q3DController
from Qgis2threejs.propertypages import DEMPropertyPage, VectorPropertyPage
from Qgis2threejs.qgis2threejscore import MapTo3D
from Qgis2threejs.qgis2threejsdialog import RectangleMapTool
from Qgis2threejs.qgis2threejstools import logMessage
from .ui.propertiesdialog import Ui_PropertiesDialog


class Q3DLiveController(Q3DController):

  def __init__(self, qgis_iface, objectTypeManager, pluginManager, serverName):
    Q3DController.__init__(self, qgis_iface, objectTypeManager, pluginManager, serverName)

    qgis_iface.mapCanvas().renderComplete.connect(self.canvasUpdated)
    qgis_iface.mapCanvas().extentsChanged.connect(self.canvasExtentChanged)

  def canvasUpdated(self, painter):
    self.iface.notify({"code": q3dconst.N_CANVAS_IMAGE_UPDATED})
    logMessage("N_CANVAS_IMAGE_UPDATED notification sent")

  def canvasExtentChanged(self):
    # update extent of export settings
    self.exportSettings.setMapCanvas(self.qgis_iface.mapCanvas())
    self.iface.notify({"code": q3dconst.N_CANVAS_EXTENT_CHANGED})
    logMessage("N_CANVAS_EXTENT_CHANGED notification sent")

  def notified(self, params):
    if params["code"] == q3dconst.N_LAYER_DOUBLECLICKED:
      self.showPropertiesDialog(params["id"], params["layerId"], params["properties"])
    else:
      Q3DController.notified(self, params)

  def processRequest(self, dataType, params):
    Q3DController.processRequest(self, dataType, params)

  def showPropertiesDialog(self, id, layerId, geomType, properties=None):
    layer = QgsMapLayerRegistry.instance().mapLayer(str(layerId))
    if layer is None:
      return

    properties = properties or {}
    dialog = PropertiesDialog(self.qgis_iface, self.objectTypeManager, self.pluginManager)
    dialog.setLayer(id, layer, geomType, properties)
    dialog.show()
    dialog.propertiesChanged.connect(self.propertiesChanged)
    dialog.exec_()

  def propertiesChanged(self, id, properties):
    self.iface.notify({"code": q3dconst.N_LAYER_PROPERTIES_CHANGED, "id": id, "properties": properties})


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

    self.setWindowTitle("Layer Properties - {0} (Qgis2threejs)".format(layer.name()))

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
