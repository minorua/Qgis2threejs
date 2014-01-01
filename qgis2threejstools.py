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
import sys
import os
import struct

try:
  from osgeo import gdal
except ImportError:
  import gdal

from gdal2threejs import Raster

debug_mode = 1

class WarpedMemoryRaster(Raster):
  def __init__(self, filename):
    Raster.__init__(self, filename)

  def read(self, width, height, wkt, geotransform, multiplier=1):
    # create a memory dataset
    driver = gdal.GetDriverByName("MEM")
    warped_ds = driver.Create("", width, height, 1, gdal.GDT_Float32)
    warped_ds.SetProjection(wkt)
    warped_ds.SetGeoTransform(geotransform)

    # reproject image
    gdal.ReprojectImage(self.ds, warped_ds, None, None, gdal.GRA_Bilinear)

    # load values into an array
    values = []
    fs = "f" * width
    band = warped_ds.GetRasterBand(1)
    for py in range(height):
      line = struct.unpack(fs, band.ReadRaster(0, py, width, 1, width, 1, gdal.GDT_Float32))
      if multiplier == 1:
        values += line
      else:
        values += map(lambda x: x * multiplier, line)
    return values

  #TODO: readValue(wkt, x, y) function, which gets value at the position using 1px * 1px memory raster
  def readValue(filename, wkt, x, y):
    pass

def warpDEM(layer, crs, extent, width, height, multiplier):
  # calculate extent. note: pixel is area in the output, but pixel should be handled as point
  xres = extent.width() / width
  yres = extent.height() / height
  geotransform = [extent.xMinimum() - xres / 2, xres, 0, extent.yMaximum() + yres / 2, 0, -yres]
  wkt = str(crs.toWkt())

  if debug_mode:
    qDebug("warpDEM: %d x %d, extent %s" % (width, height, str(geotransform)))

  warped_dem = WarpedMemoryRaster(layer.source())
  values = warped_dem.read(width + 1, height + 1, wkt, geotransform, multiplier)
  warped_dem.close()
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

def copyThreejsFiles(out_dir):
  template_dir = pluginDir() + "/threejs"
  filenames = QDir(template_dir).entryList()
  for filename in filenames:
    target = os.path.join(out_dir, filename)
    if not os.path.exists(target):
      QFile.copy(os.path.join(template_dir, filename), target)

def removeTemporaryFiles(filelist):
  try:
    for file in filelist:
      QFile.remove(file)
  except:
    qDebug("Failed to remove temporary files")

def pluginDir():
  return os.path.dirname(QFile.decodeName(__file__))

def temporaryOutputDir():
  return QDir.tempPath() + "/Qgis2threejs"
