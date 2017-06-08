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
import os
import configparser
import re
import shutil
import webbrowser

from PyQt5.QtCore import qDebug, QProcess, QSettings, QUrl, QBuffer, QByteArray, QIODevice, QFile, QDir, QFileInfo
from PyQt5.QtWidgets import QMessageBox
from qgis.core import NULL, QgsMessageLog, QgsProject

from .conf import debug_mode

def getLayersInProject():
  layers = []
  for tLayer in QgsProject.instance().layerTreeRoot().findLayers():
    layers.append(tLayer.layer())
  return layers

  #TODO: QgsProject.instance().layerTreeRoot() is a QgsLayerTree object?
  return QgsProject.instance().layerTreeRoot().layerOrder()


def getLayersByLayerIds(layerIds):
  layers = []
  for id in layerIds:
    layer = QgsProject.instance().mapLayer(id)
    if layer:
      layers.append(layer)
  return layers


def pyobj2js(obj, escape=False, quoteHex=True):
  if isinstance(obj, dict):
    items = ["{0}:{1}".format(k, pyobj2js(v, escape, quoteHex)) for k, v in obj.items()]
    return "{" + ",".join(items) + "}"
  elif isinstance(obj, list):
    items = [str(pyobj2js(v, escape, quoteHex)) for v in obj]
    return "[" + ",".join(items) + "]"
  elif isinstance(obj, bool):
    return "true" if obj else "false"
  elif isinstance(obj, str):
    if escape:
      return '"' + obj.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if not quoteHex and re.match("0x[0-9A-Fa-f]+$", obj):
      return obj
    return '"' + obj + '"'
  elif isinstance(obj, bytes):
    return pyobj2js(obj.decode("UTF-8"), escape, quoteHex)
  elif isinstance(obj, (int, float)):
    return obj
  elif obj == NULL:   # qgis.core.NULL
    return "null"
  return '"' + str(obj) + '"'


def logMessage(message):
  QgsMessageLog.logMessage(str(message), "Qgis2threejs")


def shortTextFromSelectedLayerIds(layerIds):
  count = len(layerIds)
  return "{0} layer{1} selected".format(count, "s" if count > 1 else "")

  #
  if count == 0:
    return "0 layer"

  layer = QgsProject.instance().mapLayer(layerIds[0])
  if layer is None:
    return "Layer not found"

  text = '"{0}"'.format(layer.name())
  if count > 1:
    text += " and {0} layer".format(count - 1)
  if count > 2:
    text += "s"
  return text


def openHTMLFile(htmlfilename):
  url = QUrl.fromLocalFile(htmlfilename).toString()
  settings = QSettings()
  browserPath = settings.value("/Qgis2threejs/browser", "", type=str)
  if browserPath == "":
    # open default web browser
    webbrowser.open(url, new=2)    # new=2: new tab if possible
  else:
    if not QProcess.startDetached(browserPath, [url]):
      QMessageBox.warning(None, "Qgis2threejs", "Cannot open browser: %s\nSet correct path in settings dialog." % browserPath)
      return False
  return True


def base64image(image):
  ba = QByteArray()
  buffer = QBuffer(ba)
  buffer.open(QIODevice.WriteOnly)
  image.save(buffer, "PNG")
  return "data:image/png;base64," + ba.toBase64().data().decode("ascii")


def getTemplateConfig(template_path):
  abspath = os.path.join(templateDir(), template_path)
  meta_path = os.path.splitext(abspath)[0] + ".txt"

  if not os.path.exists(meta_path):
    return {}
  parser = configparser.ConfigParser()
  parser.read(meta_path)
  config = {"path": abspath}
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

  ret = QFile.copy(source, dest)
  if debug_mode:
    if ret:
      qDebug("File copied: %s to %s" % (source, dest))
    else:
      qDebug("Failed to copy file: %s to %s" % (source, dest))
  return ret


def copyDir(source, dest, overwrite=False):
  if os.path.exists(dest):
    if overwrite:
      if debug_mode:
        qDebug("Existing dir removed: %s" % dest)
      shutil.rmtree(dest)
    else:
      if debug_mode:
        qDebug("Dir already exists: %s" % dest)
      return False

  shutil.copytree(source, dest)
  if debug_mode:
    qDebug("Dir copied: %s to %s" % (source, dest))
  return True


def copyFiles(filesToCopy, out_dir):
  plugin_dir = pluginDir()
  for item in filesToCopy:
    dest_dir = os.path.join(out_dir, item.get("dest", ""))
    subdirs = item.get("subdirs", False)
    overwrite = item.get("overwrite", False)

    if debug_mode:
      qDebug(str(item))
      qDebug("dest dir: %s" % dest_dir)

    # make destination directory
    QDir().mkpath(dest_dir)

    # copy files
    for f in item.get("files", []):
      fi = QFileInfo(f)
      dest = os.path.join(dest_dir, fi.fileName())
      if fi.isRelative():
        copyFile(os.path.join(plugin_dir, f), dest, overwrite)
      else:
        copyFile(f, dest, overwrite)

    # copy directories
    for d in item.get("dirs", []):
      fi = QFileInfo(d)
      source = os.path.join(plugin_dir, d) if fi.isRelative() else d
      dest = os.path.join(dest_dir, fi.fileName())
      if subdirs:
        copyDir(source, dest, overwrite)
      else:
        # make destination directory
        QDir().mkpath(dest)

        # copy files in the source directory
        filenames = QDir(source).entryList(QDir.Files)
        for filename in filenames:
          copyFile(os.path.join(source, filename), os.path.join(dest, filename), overwrite)


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
