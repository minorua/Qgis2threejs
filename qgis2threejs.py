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
import os
import math
import codecs
import datetime
from gdal2threejs import gdal2threejs

class Qgis2threejs:

  def __init__(self, iface):
    # Save reference to the QGIS interface
    self.iface = iface
    self.apiChanged22 = False   # not QgsApplication.prefixPath().startswith("C:/OSGeo4W")  # QGis.QGIS_VERSION_INT >= 20200

    # initialize plugin directory
    self.plugin_dir = os.path.dirname(__file__)
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
    tempOutDir = QDir(self.temporaryOutputDir())
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
    scaleDenominator = math.floor((width * height / 40000) ** 0.5)
    if scaleDenominator > 1:
      width = int(width / scaleDenominator)
      height = int(height / scaleDenominator)

    xres = extent.width() / width
    yres = extent.height() / height
    ui.lineEdit_HRes.setText(str(xres))
    ui.lineEdit_VRes.setText(str(yres))
    ui.lineEdit_Width.setText(str(width))
    ui.lineEdit_Height.setText(str(height))
    ui.lineEdit_OutputFilename.setPlaceholderText("[Temporary file]")
    ui.lineEdit_OutputFilename.setText(self.lastOutputFilename)

    # show dialog
    if not dialog.exec_():
      return

    temp_dir = QDir.tempPath()
    timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

    layerid = ui.comboBox_DEMLayer.itemData(ui.comboBox_DEMLayer.currentIndex())
    layer = QgsMapLayerRegistry().instance().mapLayer(layerid)
    self.lastDEMLayerId = layerid

    width = int(ui.lineEdit_Width.text())
    height = int(ui.lineEdit_Height.text())

    htmlfilename = ui.lineEdit_OutputFilename.text()
    if htmlfilename == "":
      htmlfilename = self.temporaryOutputDir() + "/%s.html" % timestamp
    else:
      self.lastOutputFilename = htmlfilename

    out_dir, filename = os.path.split(htmlfilename)
    if not QDir(out_dir).exists():
      QDir().mkpath(out_dir)

    filetitle = os.path.splitext(filename)[0]
    demfilename = os.path.join(temp_dir, "dem%s.tif" % timestamp)
    jsfilename = os.path.splitext(htmlfilename)[0] + ".js"

    # save map canvas image
    texfilename = os.path.join(temp_dir, "tex%s.png" % (timestamp))
    self.iface.mapCanvas().saveAsImage(texfilename)

    # generate dem file
    # gdalwarp options
    options = []
    options.append("-r bilinear")

    # calculate extent. note: pixel is area in the output geotiff, but pixel should be handled as point
    xres = extent.width() / width
    yres = extent.height() / height
    ext = (extent.xMinimum() - xres / 2, extent.yMinimum() - yres / 2, extent.xMaximum() + xres / 2, extent.yMaximum() + yres / 2)
    options.append("-te %f %f %f %f" % ext)
    options.append("-ts %d %d" % (width + 1, height + 1))

    # target crs
    mapSettings = self.iface.mapCanvas().mapSettings() if self.apiChanged22 else self.iface.mapCanvas().mapRenderer()
    authid = mapSettings.destinationCrs().authid()
    if authid.startswith("EPSG:"):
      options.append("-t_srs %s" % authid)
    else:
      options.append('-t_srs "%s"' % mapSettings.destinationCrs().toProj4())

    options.append('"' + layer.source() + '"')
    options.append('"' + demfilename + '"')

    # run gdalwarp command
    cmd = "gdalwarp " + " ".join(options)
    #QMessageBox.information(None, "Qgis2threejs", "\n".join([htmlfilename, cmd]))
    os.system(cmd)
    if not os.path.exists(demfilename):
      QMessageBox.warning(None, "Qgis2threejs", "Failed to generate a dem file using gdalwarp")
      return

    # copy files from template
    template_dir = os.path.dirname(QFile.decodeName(__file__)) + "/template"
    filenames = QDir(template_dir).entryList()
    filenames.remove("index.html")
    for filename in filenames:
      target = os.path.join(out_dir, filename)
      if not os.path.exists(target):
        QFile.copy(os.path.join(template_dir, filename), target)

    # generate data file
    err = gdal2threejs(demfilename, texfilename, jsfilename, filetitle)
    if err:
      QMessageBox.warning(None, "Qgis2threejs", err)
      return

    # generate html file
    with codecs.open(os.path.join(template_dir, "index.html"), "r", "UTF-8") as f:
      html = f.read()

    with codecs.open(htmlfilename, "w", "UTF-8") as f:
      f.write(html.replace("${title}", filetitle).replace("${datafile}", filetitle + ".js"))

    # remove temporary files
    try:
      QFile.remove(demfilename)
      QFile.remove(texfilename)
      QFile.remove(texfilename + "w")
    except:
      qDebug("Failed to remove temporary files")

    # open webbrowser
    import webbrowser
    webbrowser.open(htmlfilename, new=2)    # new=2: new tab if possible

  def temporaryOutputDir(self):
    return QDir.tempPath() + "/Qgis2threejs"
