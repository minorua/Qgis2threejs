# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2013-12-29

import os
import base64
import configparser
import re
import shutil

from PyQt5.QtCore import qDebug, QBuffer, QByteArray, QDir, QFile, QFileInfo, QIODevice, QProcess, QSettings, QUrl, QUuid
from PyQt5.QtGui import QDesktopServices
from qgis.core import NULL, Qgis, QgsMapLayer, QgsMessageLog, QgsProject

from .conf import DEBUG_MODE


def getLayersInProject():
    layers = []
    for tl in QgsProject.instance().layerTreeRoot().findLayers():
        if tl.layer():
            layers.append(tl.layer())
    return layers


def getDEMLayersInProject():
    layers = []
    for layer in getLayersInProject():
        if layer.type() == QgsMapLayer.RasterLayer:
            if layer.providerType() == "gdal" and layer.bandCount() == 1:
                layers.append(layer)
    return layers


def getLayersByLayerIds(layerIds):
    layers = []
    for id in layerIds:
        layer = QgsProject.instance().mapLayer(id)
        if layer:
            layers.append(layer)
    return layers


def js_bool(o):
    return "true" if o else "false"


def css_color(c):
    if isinstance(c, list):
        if len(c) == 4 and c[3] != 255:
            return "rgba({},{},{},{:.2f})".format(*c[:3], c[3] / 255)

        return "rgb({},{},{})".format(*c[:3])

    return str(c).replace("0x", "#") if c else "#000000"


def hex_color(c, prefix="#"):
    if isinstance(c, list):
        return "{}{:x}{:x}{:x}".format(prefix, *c[:3])

    if not c and prefix == "#":
        return "#000000"

    return prefix + str(c or 0).replace("0x", "").replace("#", "")


def int_color(c):
    if isinstance(c, list):
        return c[0] * 256 * 256 + c[1] * 256 + c[2]

    if isinstance(c, str):
        return int(c.replace("#", "0x") or "0", 16)

    return 0


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


def abchex(number):
    h = ""
    for c in "{:x}".format(number):
        i = ord(c)
        if i >= 97:   # a - f => k - p
            h += chr(i + 10)
        else:         # 0 - 9 => a - j
            h += chr(i + 49)
    return h


# parse a string to a integer number. if failed, return def_val.
def parseInt(string, def_val=None):
    try:
        return int(string)
    except (TypeError, ValueError):
        return def_val


# parse a string to a floating point number. if failed, return def_val.
def parseFloat(string, def_val=None):
    try:
        return float(string)
    except (TypeError, ValueError):
        return def_val


def createUid():
    return QUuid.createUuid().toString()[1:9]


def logMessage(message, warning=True, error=False):
    level = Qgis.Critical if error else (Qgis.Warning if warning else Qgis.Info)
    QgsMessageLog.logMessage(str(message), "Qgis2threejs", level, warning or error)


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


def openUrl(url):
    """url: QUrl object"""
    if url.fileName().endswith((".html", ".htm")):
        settings = QSettings()
        browserPath = settings.value("/Qgis2threejs/browser", "", type=str)
        if browserPath:
            if QProcess.startDetached(browserPath, [url.toString()]):
                return
            else:
                logMessage("Incorrect web browser path. Open URL using default web browser.", True)

    QDesktopServices.openUrl(url)


def openDirectory(dir_path):
    QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))


def base64image(image):
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, "PNG")
    return "data:image/png;base64," + ba.toBase64().data().decode("ascii")


def base64file(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except:
        logMessage("Cannot read file: {}".format(file_path))
        return None


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
    if DEBUG_MODE:
        qDebug("config: " + str(config))
    return config


def copyFile(source, dest, overwrite=False):
    if os.path.exists(dest):
        if overwrite or abs(QFileInfo(source).lastModified().secsTo(QFileInfo(dest).lastModified())) > 5:   # use secsTo for different file systems
            if DEBUG_MODE:
                qDebug("Existing file removed: %s (%s, %s)" % (dest, str(QFileInfo(source).lastModified()), str(QFileInfo(dest).lastModified())))
            QFile.remove(dest)
        else:
            if DEBUG_MODE:
                qDebug("File already exists: %s" % dest)
            return False

    ret = QFile.copy(source, dest)
    if DEBUG_MODE:
        if ret:
            qDebug("File copied: %s to %s" % (source, dest))
        else:
            qDebug("Failed to copy file: %s to %s" % (source, dest))
    return ret


def copyDir(source, dest, overwrite=False):
    if os.path.exists(dest):
        if overwrite:
            if DEBUG_MODE:
                qDebug("Existing dir removed: %s" % dest)
            shutil.rmtree(dest)
        else:
            if DEBUG_MODE:
                qDebug("Dir already exists: %s" % dest)
            return False

    shutil.copytree(source, dest)
    if DEBUG_MODE:
        qDebug("Dir copied: %s to %s" % (source, dest))
    return True


def copyFiles(filesToCopy, out_dir):
    plugin_dir = pluginDir()
    for item in filesToCopy:
        dest_dir = os.path.join(out_dir, item.get("dest", ""))
        subdirs = item.get("subdirs", False)
        overwrite = item.get("overwrite", False)

        if DEBUG_MODE:
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


def pluginDir(*subdirs):
    p = os.path.dirname(__file__)
    if subdirs:
        return os.path.join(p, *subdirs)
    return p


def templateDir():
    return pluginDir("html_templates")


def temporaryOutputDir():
    return QDir.tempPath() + "/Qgis2threejs"


def settingsFilePath():
    proj_path = QgsProject.instance().fileName()
    return proj_path + ".qto3settings" if proj_path else None
