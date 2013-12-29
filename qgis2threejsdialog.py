# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejsDialog
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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
from ui_qgis2threejsdialog import Ui_Qgis2threejsDialog

import sys
import os
import codecs
import datetime
import webbrowser

import gdal2threejs
import qgis2threejstools as tools
from quadtree import *

debug_mode = 1

class Qgis2threejsDialog(QDialog):
  def __init__(self, iface):
    QDialog.__init__(self, iface.mainWindow())
    self.iface = iface
    self.apiChanged22 = False   # not QgsApplication.prefixPath().startswith("C:/OSGeo4W")  # QGis.QGIS_VERSION_INT >= 20200

    # Set up the user interface from Designer.
    self.ui = ui = Ui_Qgis2threejsDialog()
    ui.setupUi(self)

    self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)
    ui.lineEdit_OutputFilename.setPlaceholderText("[Temporary file]")
    ui.toolButton_Browse.clicked.connect(self.browseClicked)
    ui.radioButton_Simple.toggled.connect(self.samplingModeToggled)
    ui.toolButton_PointTool.clicked.connect(self.startPointSelection)
    ui.toolButton_PointTool.setVisible(False)

    self.rb_quads = self.rb_point = None

    # set map tool
    self.previousMapTool = None
    self.mapTool = PointMapTool(iface.mapCanvas())
    QObject.connect(self.mapTool, SIGNAL("pointSelected()"), self.pointSelected)
    iface.mapCanvas().mapToolSet.connect(self.mapToolSet)
    self.startPointSelection()

  def runSimple(self):
    ui = self.ui
    extent = self.iface.mapCanvas().extent()
    mapSettings = self.iface.mapCanvas().mapSettings() if self.apiChanged22 else self.iface.mapCanvas().mapRenderer()
    temp_dir = QDir.tempPath()
    timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

    demlayerid = ui.comboBox_DEMLayer.itemData(ui.comboBox_DEMLayer.currentIndex())
    demlayer = QgsMapLayerRegistry().instance().mapLayer(demlayerid)

    htmlfilename = ui.lineEdit_OutputFilename.text()
    if htmlfilename == "":
      htmlfilename = tools.temporaryOutputDir() + "/%s.html" % timestamp

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
    width = int(ui.lineEdit_Width.text())
    height = int(ui.lineEdit_Height.text())
    if os.path.exists(demfilename):
      QFile.remove(demfilename)
    err = tools.generateDEM(demlayer, mapSettings.destinationCrs(), extent, width, height, demfilename)
    if err:
      QMessageBox.warning(None, "Qgis2threejs", err)
      return

    # generate javascript data file
    fsenc = sys.getfilesystemencoding()
    err = gdal2threejs.gdal2threejs(demfilename.encode(fsenc), texfilename.encode(fsenc), jsfilename.encode(fsenc), filetitle, "[0]")
    if err:
      QMessageBox.warning(None, "Qgis2threejs", err)
      return

    # copy files from template
    tools.copyThreejsFiles(out_dir)

    # generate html file
    with codecs.open(tools.pluginDir() + "/template.html", "r", "UTF-8") as f:
      html = f.read()

    with codecs.open(htmlfilename, "w", "UTF-8") as f:
      f.write(html.replace("${title}", filetitle).replace("${scripts}", '<script src="./%s.js"></script>' % filetitle))

    # remove temporary files
    tools.removeTemporaryFiles([demfilename, texfilename, texfilename + "w"])

    # open webbrowser
    webbrowser.open(htmlfilename, new=2)    # new=2: new tab if possible

  def runAdvanced(self):
    ui = self.ui
    canvas = self.iface.mapCanvas()
    mapSettings = canvas.mapSettings() if self.apiChanged22 else canvas.mapRenderer()
    temp_dir = QDir.tempPath()
    timestamp = datetime.datetime.today().strftime("%Y%m%d%H%M%S")

    demlayerid = ui.comboBox_DEMLayer.itemData(ui.comboBox_DEMLayer.currentIndex())
    demlayer = QgsMapLayerRegistry().instance().mapLayer(demlayerid)

    htmlfilename = ui.lineEdit_OutputFilename.text()
    if htmlfilename == "":
      htmlfilename = tools.temporaryOutputDir() + "/%s.html" % timestamp

    out_dir, filename = os.path.split(htmlfilename)
    if not QDir(out_dir).exists():
      QDir().mkpath(out_dir)
    filetitle = os.path.splitext(filename)[0]

    # create quad tree
    point = QgsPoint(float(ui.lineEdit_CenterX.text()), float(ui.lineEdit_CenterY.text()))
    quadtree = QuadTree(canvas.extent(), point, ui.spinBox_Depth.value())
    quads = quadtree.quads()

    # create quads and a point on map canvas with rubber bands
    self.createRubberBands(quads, point)

    # create an image for texture
    hpw = canvas.extent().height() / canvas.extent().width()
    if hpw < 1:
      image_width = 256
      image_height = round(image_width * hpw)
    else:
      image_height = 256
      image_width = round(image_height * hpw)
    image = QImage(image_width, image_height, QImage.Format_ARGB32_Premultiplied)
    self.log("Created image size: %d, %d" % (image_width, image_height))

    layerids = []
    for layer in canvas.layers():
      layerids.append(unicode(layer.id()))

    # set up a renderer
    labeling = QgsPalLabeling()
    renderer = QgsMapRenderer()
    renderer.setOutputSize(image.size(), image.logicalDpiX())
    renderer.setDestinationCrs(mapSettings.destinationCrs())
    renderer.setProjectionsEnabled(True)
    renderer.setLabelingEngine(labeling)
    renderer.setLayerSet(layerids)

    painter = QPainter(image)
    antialias = True
    if antialias:
      painter.setRenderHint(QPainter.Antialiasing)

    # (currently) dem size should be 2 ^ quadtree.depth * a, where a is larger integer than 0
    # with smooth resolution change, this is not necessary
    dem_width = dem_height = max(128, 2 ** quadtree.depth)
    terrain_width = 100
    terrain_height = 100 * canvas.extent().height() / canvas.extent().width()
    scale = 1.5
    multiplier = 100 * scale / canvas.extent().width()

    for i, quad in enumerate(quads):
      extent = quad.extent
      demfilename = os.path.join(temp_dir, "%s_%d.tif" % (timestamp, i))
      texfilename = os.path.join(temp_dir, "%s_%d.png" % (timestamp, i))
      jsfilename = os.path.splitext(htmlfilename)[0] + "_%d.js" % i

      # render map image
      image.fill(QColor(255,255,255))
      renderer.setExtent(extent)
      renderer.render(painter)
      image.save(texfilename)    #TODO: output into memory

      # generate DEM file
      if os.path.exists(demfilename):
        QFile.remove(demfilename)
      tools.generateDEM(demlayer, mapSettings.destinationCrs(), extent, dem_width, dem_height, demfilename)

      # generate javascript data file
      width = terrain_width * extent.width() / canvas.extent().width()
      height = terrain_height * extent.height() / canvas.extent().height()
      offsetX = terrain_width * (extent.xMinimum() - canvas.extent().xMinimum()) / canvas.extent().width() + width / 2 - terrain_width / 2
      offsetY = terrain_height * (extent.yMinimum() - canvas.extent().yMinimum()) / canvas.extent().height() + height / 2 - terrain_height / 2

      dem = gdal2threejs.Raster(demfilename)
      dem_values = dem.read(multiplier)
      dem.close()

      # value resampling on edges for combination with different resolution DEM
      neighbors = quadtree.neighbors(quad)
      self.log("Output quad (%d %s): depth=%d" % (i, str(quad), quad.depth))
      for direction, neighbor in enumerate(neighbors):
        if neighbor is None:
          continue
        self.log(" neighbor %d %s: depth=%d" % (direction, str(neighbor), neighbor.depth))
        interval = 2 ** (quad.depth - neighbor.depth)
        if interval > 1:
          if direction == QuadTree.UP or direction == QuadTree.DOWN:
            y = 0 if direction == QuadTree.UP else dem.height - 1
            for x1 in range(interval, dem.width, interval):
              x0 = x1 - interval
              z0 = dem_values[x0 + dem.width * y]
              z1 = dem_values[x1 + dem.width * y]
              for xx in range(1, interval):
                z = (z0 * (interval - xx) + z1 * xx) / interval
                dem_values[x0 + xx + dem.width * y] = z
          else:   # LEFT or RIGHT
            x = 0 if direction == QuadTree.LEFT else dem.width - 1
            for y1 in range(interval, dem.height, interval):
              y0 = y1 - interval
              z0 = dem_values[x + dem.width * y0]
              z1 = dem_values[x + dem.width * y1]
              for yy in range(1, interval):
                z = (z0 * (interval - yy) + z1 * yy) / interval
                dem_values[x + dem.width * (y0 + yy)] = z

      tex = gdal2threejs.base64image(texfilename)
      suffix = "[%d]" % i
      with open(jsfilename, "w") as f:
        opt = "{width:%f,height:%f,offsetX:%f,offsetY:%f}" % (width, height, offsetX, offsetY)
        f.write('dem%s = {width:%d,height:%d,plane:%s,data:[%s]};\n' % (suffix, dem.width, dem.height, opt, ",".join(map(gdal2threejs.formatValue, dem_values))))
        f.write('tex%s = "%s";\n' % (suffix, tex))

      tools.removeTemporaryFiles([demfilename, texfilename, texfilename + "w"])

    # copy files from template
    tools.copyThreejsFiles(out_dir)

    # generate html file
    with codecs.open(tools.pluginDir() + "/template.html", "r", "UTF-8") as f:
      html = f.read()

    scripts = []
    for i in range(len(quads)):
      scripts.append('<script src="./%s_%d.js"></script>' % (filetitle, i))

    with codecs.open(htmlfilename, "w", "UTF-8") as f:
      f.write(html.replace("${title}", filetitle).replace("${scripts}", "\n".join(scripts)))

    # open webbrowser
    webbrowser.open(htmlfilename, new=2)    # new=2: new tab if possible

  def accept(self):
    filename = self.ui.lineEdit_OutputFilename.text()   # ""=Temporary file
    if filename != "" and QFileInfo(filename).exists() and QMessageBox.question(None, "Qgis2threejs", "Output file already exists. Overwrite it?", QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
      return
    self.endPointSelection()
    self.setVisible(False)
    if self.ui.radioButton_Simple.isChecked():
      self.runSimple()
    else:
      self.runAdvanced()
    self.clearRubberBands()
    QDialog.accept(self)

  def reject(self):
    self.endPointSelection()
    self.clearRubberBands()
    QDialog.reject(self)

  def startPointSelection(self):
    canvas = self.iface.mapCanvas()
    self.previousMapTool = canvas.mapTool()
    canvas.setMapTool(self.mapTool)
    self.ui.toolButton_PointTool.setVisible(False)

  def endPointSelection(self):
    self.iface.mapCanvas().setMapTool(self.previousMapTool)

  def pointSelected(self):
    # set values of controls
    self.ui.lineEdit_CenterX.setText(str(self.mapTool.point.x()))
    self.ui.lineEdit_CenterY.setText(str(self.mapTool.point.y()))
    self.ui.radioButton_Advanced.setChecked(True)

    quadtree = QuadTree(self.iface.mapCanvas().extent(), self.mapTool.point, self.ui.spinBox_Depth.value())
    self.createRubberBands(quadtree.quads(), self.mapTool.point)
    self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive);

  def mapToolSet(self, mapTool):
    if mapTool != self.mapTool:
      self.ui.toolButton_PointTool.setVisible(True)

  def createRubberBands(self, quads, point=None):
    self.clearRubberBands()
    # create quads with rubber band
    self.rb_quads = QgsRubberBand(self.iface.mapCanvas(), QGis.Line)
    self.rb_quads.setColor(Qt.blue)
    self.rb_quads.setWidth(1)

    for quad in quads:
      points = []
      extent = quad.extent
      points.append(QgsPoint(extent.xMinimum(), extent.yMinimum()))
      points.append(QgsPoint(extent.xMinimum(), extent.yMaximum()))
      points.append(QgsPoint(extent.xMaximum(), extent.yMaximum()))
      points.append(QgsPoint(extent.xMaximum(), extent.yMinimum()))
      self.rb_quads.addGeometry(QgsGeometry.fromPolygon([points]), None)
      self.log(extent.toString())
    self.log("Quad count: %d" % len(quads))

    # create a point with rubber band
    if point:
      self.rb_point = QgsRubberBand(self.iface.mapCanvas(), QGis.Point)
      self.rb_point.setColor(Qt.red)
      self.rb_point.addPoint(point)

  def clearRubberBands(self):
    # clear quads and point
    if self.rb_quads:
      self.iface.mapCanvas().scene().removeItem(self.rb_quads)
      self.rb_quads = None
    if self.rb_point:
      self.iface.mapCanvas().scene().removeItem(self.rb_point)
      self.rb_point = None

  def browseClicked(self):
    directory = self.ui.lineEdit_OutputFilename.text()
    if directory == "":
      directory = QDir.homePath()
    filename = QFileDialog.getSaveFileName(self, self.tr("Output filename"), directory, "HTML file (*.html *.htm)", options=QFileDialog.DontConfirmOverwrite)
    if filename != "":
      self.ui.lineEdit_OutputFilename.setText(filename)

  def samplingModeToggled(self):
    ui = self.ui
    isSimpleMode = ui.radioButton_Simple.isChecked()
    isAdvancedMode = not isSimpleMode
    ui.spinBox_Depth.setEnabled(isAdvancedMode)
    ui.lineEdit_CenterX.setEnabled(isAdvancedMode)
    ui.lineEdit_CenterY.setEnabled(isAdvancedMode)

  def log(self, msg):
    if debug_mode:
      qDebug(msg)

class PointMapTool(QgsMapToolEmitPoint):
  def __init__(self, canvas):
    self.canvas = canvas
    QgsMapToolEmitPoint.__init__(self, self.canvas)
    self.point = None

  def canvasPressEvent(self, e):
    self.point = self.toMapCoordinates(e.pos())
    self.emit(SIGNAL("pointSelected()"))
