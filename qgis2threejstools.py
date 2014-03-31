# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
                              -------------------
        begin                : 2013-12-29
        copyright            : (C) 2013 Minoru Akagi
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
from PyQt4.QtGui import QMessageBox
import sys
import os
import ConfigParser
import shutil
import struct
import base64
import webbrowser

try:
  from osgeo import gdal
except ImportError:
  import gdal

from gdal2threejs import Raster

debug_mode = 1

class MemoryWarpRaster(Raster):
  def __init__(self, filename):
    Raster.__init__(self, filename)
    self.driver = gdal.GetDriverByName("MEM")

  def read(self, width, height, wkt, geotransform):
    # create a memory dataset
    warped_ds = self.driver.Create("", width, height, 1, gdal.GDT_Float32)
    warped_ds.SetProjection(wkt)
    warped_ds.SetGeoTransform(geotransform)

    # reproject image
    gdal.ReprojectImage(self.ds, warped_ds, None, None, gdal.GRA_Bilinear)

    # load values into an array
    values = []
    fs = "f" * width
    band = warped_ds.GetRasterBand(1)
    for py in range(height):
      values += struct.unpack(fs, band.ReadRaster(0, py, width, 1, width, 1, gdal.GDT_Float32))
    return values

  def readValue(self, wkt, x, y):
    # get value at the position using 1px * 1px memory raster
    res = 0.1
    geotransform = [x - res / 2, res, 0, y + res / 2, 0, -res]
    return self.read(1, 1, wkt, geotransform)[0]

class FlatRaster:
  def __init__(self, value=0):
    self.value = value

  def read(self, width, height, wkt, geotransform):
    return [self.value] * width * height

  def readValue(self, wkt, x, y):
    return self.value

def warpDEM(layer, crs, extent, width, height, multiplier):
  # calculate extent. output dem should be handled as points.
  xres = extent.width() / (width - 1)
  yres = extent.height() / (height - 1)
  geotransform = [extent.xMinimum() - xres / 2, xres, 0, extent.yMaximum() + yres / 2, 0, -yres]
  wkt = str(crs.toWkt())

  if debug_mode:
    qDebug("warpDEM: %d x %d, extent %s" % (width, height, str(geotransform)))

  warped_dem = MemoryWarpRaster(layer.source().encode("UTF-8"))
  values = warped_dem.read(width, height, wkt, geotransform)
  warped_dem.close()
  if multiplier != 1:
    values = map(lambda x: x * multiplier, values)
  return values

def generateDEM(layer, crs, extent, width, height, demfilename):
  # generate dem file
  # gdalwarp options
  options = []
  options.append("--config GDAL_FILENAME_IS_UTF8 NO")
  options.append("-r bilinear")

  # calculate extent. note: pixel is area in the output geotiff, but pixel should be handled as point
  xres = extent.width() / width
  yres = extent.height() / height
  ext = (extent.xMinimum() - xres / 2, extent.yMinimum() - yres / 2, extent.xMaximum() + xres / 2, extent.yMaximum() + yres / 2)
  options.append("-te %f %f %f %f" % ext)
  options.append("-ts %d %d" % (width + 1, height + 1))

  # target crs
  authid = crs.authid()
  if authid.startswith("EPSG:"):
    options.append("-t_srs %s" % authid)
  else:
    options.append('-t_srs "%s"' % crs.toProj4())

  options.append('"' + layer.source() + '"')
  options.append('"' + demfilename + '"')

  # run gdalwarp command
  cmd = "gdalwarp " + u" ".join(options)
  if debug_mode:
    qDebug(cmd.encode("UTF-8"))
  process = QProcess()
  process.start(cmd)
  process.waitForFinished()
  if not os.path.exists(demfilename):
    hint = ""
    if os.system("gdalwarp --help-general"):
      hint = "gdalwarp is not installed."
    return "Failed to generate a dem file using gdalwarp. " + hint
  return 0

def openHTMLFile(htmlfilename):
  settings = QSettings()
  browserPath = settings.value("/Qgis2threejs/browser", "", type=unicode)
  if browserPath == "":
    # open default web browser
    webbrowser.open(htmlfilename, new=2)    # new=2: new tab if possible
  else:
    if not QProcess.startDetached(browserPath, [QUrl.fromLocalFile(htmlfilename).toString()]):
      QMessageBox.warning(None, "Qgis2threejs", "Cannot open browser: %s\nSet correct path in settings dialog." % browserPath)
      return False
  return True

def base64image(image):
  ba = QByteArray()
  buffer = QBuffer(ba)
  buffer.open(QIODevice.WriteOnly)
  image.save(buffer, "PNG")
  return "data:image/png;base64," + base64.b64encode(ba)

def getTemplateMetadata(template_path):
  meta_path = os.path.splitext(template_path)[0] + ".txt"
  if not os.path.exists(meta_path):
    return {}
  parser = ConfigParser.SafeConfigParser()
  with open(meta_path, "r") as f:
    parser.readfp(f)
  metadata = {}
  for item in parser.items("general"):
    metadata[item[0]] = item[1]
  if debug_mode:
    qDebug("metadata" + str(metadata))
  return metadata

def copyLibraries(out_dir, metadata, overwrite=False):
  plugin_dir = pluginDir()
  files = metadata.get("files", "").strip()
  if files:
    for f in files.split(","):
      filepath = os.path.join(plugin_dir, f)
      filename = os.path.basename(f)
      target = os.path.join(out_dir, filename)
      if overwrite or not os.path.exists(target):
        if debug_mode:
          qDebug("Copy file: %s to %s" % (filepath, target))
        QFile.copy(filepath, target)
      #TODO: message if already exists

  dirs = metadata.get("dirs", "").strip()
  if dirs:
    for d in dirs.split(","):
      dirpath = os.path.join(plugin_dir, d)
      dirname = os.path.basename(d)
      target = os.path.join(out_dir, dirname)
      if overwrite or not os.path.exists(target):
        if debug_mode:
          qDebug("Copy dir: %s to %s" % (dirpath, target))
        shutil.copytree(dirpath, target)
      #TODO: message if already exists

def copyThreejsFiles(out_dir, controls="TrackballControls.js", overwrite=True):
  threejs_dir= pluginDir() + "/js/threejs"

  # make directory
  target_dir = os.path.join(out_dir, "threejs")
  QDir().mkpath(target_dir)

  # copy files in threejs directory
  filenames = QDir(threejs_dir).entryList(QDir.Files)
  for filename in filenames:
    target = os.path.join(target_dir, filename)
    if overwrite or not os.path.exists(target):
      QFile.copy(os.path.join(threejs_dir, filename), target)
    #TODO: message if already exists

  # copy controls file
  ctrl_path = os.path.join(threejs_dir, "controls", controls)
  target = os.path.join(target_dir, controls)
  if overwrite or not os.path.exists(target):
    QFile.copy(ctrl_path, target)
  #TODO: message if already exists

def removeTemporaryFiles(filelist):
  for file in filelist:
    QFile.remove(file)

def removeTemporaryOutputDir():
  removeDir(temporaryOutputDir())

def removeDir(dirName):
  d = QDir(dirName)
  if d.exists():
    for info in d.entryInfoList(QDir.Dirs | QDir.Files | QDir.NoDotAndDotDot):
      if info.isDir():
        removeDir(info.absoluteFilePath())
      else:
        d.remove(info.fileName())
    d.rmdir(dirName)

def pluginDir():
  return os.path.dirname(QFile.decodeName(__file__))

def templateDir():
  return os.path.join(pluginDir(), "html_templates")

def temporaryOutputDir():
  return QDir.tempPath() + "/Qgis2threejs"
