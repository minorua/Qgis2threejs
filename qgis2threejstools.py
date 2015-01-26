# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
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
from PyQt4.QtCore import qDebug, QProcess, QSettings, QUrl, QByteArray, QBuffer, QIODevice, QFile, QDir, QFileInfo
from PyQt4.QtGui import QMessageBox
import os
import ConfigParser
import re
import shutil
import webbrowser

debug_mode = 1

def pyobj2js(obj, escape=False, quoteHex=True):
  if isinstance(obj, dict):
    items = [u"{0}:{1}".format(k, pyobj2js(v, escape, quoteHex)) for k, v in obj.iteritems()]
    return "{" + ",".join(items) + "}"
  elif isinstance(obj, list):
    items = [unicode(pyobj2js(v, escape, quoteHex)) for v in obj]
    return "[" + ",".join(items) + "]"
  elif isinstance(obj, bool):
    return "true" if obj else "false"
  elif isinstance(obj, (str, unicode)):
    if escape:
      return '"' + obj.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if not quoteHex and re.match("0x[0-9A-Fa-f]+$", obj):
      return obj
    return '"' + obj + '"'
  elif isinstance(obj, (int, float)):
    return obj
  elif obj == NULL:   # qgis.core.NULL
    return "null"
  return '"' + str(obj) + '"'

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
  return "data:image/png;base64," + ba.toBase64().data()

def getTemplateConfig(template_path):
  meta_path = os.path.splitext(template_path)[0] + ".txt"
  if not os.path.exists(meta_path):
    return {}
  parser = ConfigParser.SafeConfigParser()
  with open(meta_path, "r") as f:
    parser.readfp(f)
  config = {"path": template_path}
  for item in parser.items("general"):
    config[item[0]] = item[1]
  if debug_mode:
    qDebug("config: " + str(config))
  return config

def copyFile(source, dest, overwrite=False):
  if os.path.exists(dest):
    if overwrite or abs(QFileInfo(source).lastModified().secsTo(QFileInfo(dest).lastModified())) > 5:   # use secsTo for different file systems
      if debug_mode:
        qDebug("Existing file removed: %s (%s, %s)" % (dest, str(QFileInfo(source).lastModified()), str(QFileInfo(dest).lastModified())))
      QFile.remove(dest)
    else:
      if debug_mode:
        qDebug("File already exists: %s" % dest)
      return False

  if debug_mode:
    qDebug("File copied: %s to %s" % (source, dest))
  return QFile.copy(source, dest)

def copyLibraries(out_dir, config, overwrite=False):
  plugin_dir = pluginDir()
  files = config.get("files", "").strip()
  if files:
    for f in files.split(","):
      filename = os.path.basename(f)
      copyFile(os.path.join(plugin_dir, f), os.path.join(out_dir, filename), overwrite)

  dirs = config.get("dirs", "").strip()
  if dirs:
    for d in dirs.split(","):
      dirpath = os.path.join(plugin_dir, d)
      dirname = os.path.basename(d)
      target = os.path.join(out_dir, dirname)
      if overwrite or not os.path.exists(target):
        if debug_mode:
          qDebug("Copy dir: %s to %s" % (dirpath, target))
        shutil.copytree(dirpath, target)

def copyProj4js(out_dir, overwrite=False):
  plugin_dir = pluginDir()
  d = "js/proj4js"
  dirpath = os.path.join(plugin_dir, d)
  dirname = os.path.basename(d)
  target = os.path.join(out_dir, dirname)
  if overwrite or not os.path.exists(target):
    if debug_mode:
      qDebug("Copy dir: %s to %s" % (dirpath, target))
    shutil.copytree(dirpath, target)

def copyThreejsFiles(out_dir, controls, overwrite=False):
  threejs_dir = pluginDir() + "/js/threejs"

  # make directory
  target_dir = os.path.join(out_dir, "threejs")
  QDir().mkpath(target_dir)

  # copy files in threejs directory
  filenames = QDir(threejs_dir).entryList(QDir.Files)
  for filename in filenames:
    copyFile(os.path.join(threejs_dir, filename), os.path.join(target_dir, filename), overwrite)

  # copy controls file
  copyFile(os.path.join(threejs_dir, "controls", controls), os.path.join(target_dir, controls), overwrite)

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
