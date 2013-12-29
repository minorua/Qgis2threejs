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

debug_mode = 1

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
