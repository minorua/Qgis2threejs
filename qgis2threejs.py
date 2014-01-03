# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
                              -------------------
        begin                : 2013-12-21
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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from qgis2threejsdialog import Qgis2threejsDialog
import qgis2threejstools as tools
import os

class Qgis2threejs:

  def __init__(self, iface):
    # Save reference to the QGIS interface
    self.iface = iface

    # initialize plugin directory
    self.plugin_dir = os.path.dirname(QFile.decodeName(__file__))
    # initialize locale
    locale = QSettings().value("locale/userLocale")[0:2]
    localePath = os.path.join(self.plugin_dir, 'i18n', 'qgis2threejs_{}.qm'.format(locale))

    if os.path.exists(localePath):
      self.translator = QTranslator()
      self.translator.load(localePath)

      if qVersion() > '4.3.3':
        QCoreApplication.installTranslator(self.translator)

    self.lastDEMLayerId = None
    self.lastOutputFilename = ""
    self.lastZFactor = "1.5"

  def initGui(self):
    # Create action that will start plugin configuration
    self.action = QAction(
      QIcon(":/plugins/qgis2threejs/icon.png"),
      u"Qgis2threejs", self.iface.mainWindow())
    # connect the action to the run method
    self.action.triggered.connect(self.run)

    # Add toolbar button and menu item
    self.iface.addToolBarIcon(self.action)
    self.iface.addPluginToMenu(u"&Qgis2threejs", self.action)

  def unload(self):
    # Remove the plugin menu item and icon
    self.iface.removePluginMenu(u"&Qgis2threejs", self.action)
    self.iface.removeToolBarIcon(self.action)

    # remove temporary output directory
    tempOutDir = QDir(tools.temporaryOutputDir())
    if tempOutDir.exists():
      try:
        for file in tempOutDir.entryList():
          tempOutDir.remove(file)
        QDir().rmdir(self.temporaryOutputDir())
      except:
        qDebug("Failed to remove temporary output directory")

  def run(self):
    extent = self.iface.mapCanvas().extent()
    renderer = self.iface.mapCanvas().mapRenderer()

    # create dialog
    dialog = Qgis2threejsDialog(self.iface)
    ui = dialog.ui
    ui.lineEdit_MapCanvasExtent.setText("%.4f, %.4f - %.4f, %.4f" % (extent.xMinimum(), extent.yMinimum(), extent.xMaximum(), extent.yMaximum()))
    ui.lineEdit_MapCanvasSize.setText("{0} x {1}".format(renderer.width(), renderer.height()))

    # list raster layers
    ui.comboBox_DEMLayer.clear()
    for id, layer in QgsMapLayerRegistry().instance().mapLayers().items():
      if layer.type() == QgsMapLayer.RasterLayer and layer.providerType() == "gdal":
        ui.comboBox_DEMLayer.addItem(layer.name(), id)

    # select the last selected layer
    if self.lastDEMLayerId is not None:
      index = ui.comboBox_DEMLayer.findData(self.lastDEMLayerId)
      if index != -1:
        ui.comboBox_DEMLayer.setCurrentIndex(index)

    # calculate resolution and size
    width, height = renderer.width(), renderer.height()
    s = (40000. / (width * height)) ** 0.5
    if s < 1:
      width = int(width * s)
      height = int(height * s)

    xres = extent.width() / width
    yres = extent.height() / height
    ui.lineEdit_HRes.setText(str(xres))
    ui.lineEdit_VRes.setText(str(yres))
    ui.lineEdit_Width.setText(str(width + 1))
    ui.lineEdit_Height.setText(str(height + 1))
    ui.lineEdit_OutputFilename.setText(self.lastOutputFilename)
    ui.lineEdit_zFactor.setText(self.lastZFactor)

    # show dialog
    dialog.show()
    if dialog.exec_():
      self.lastOutputFilename = ui.lineEdit_OutputFilename.text()
      self.lastDEMLayerId = ui.comboBox_DEMLayer.itemData(ui.comboBox_DEMLayer.currentIndex())
      self.lastZFactor = ui.lineEdit_zFactor.text()
