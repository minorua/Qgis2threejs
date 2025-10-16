# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import base64
import configparser
import re
import shutil
from datetime import datetime

from qgis.PyQt.QtCore import qDebug as qDebugA, QBuffer, QByteArray, QDir, QFile, QFileInfo, QIODevice, QObject, QProcess, QSettings, QUrl, QUuid, pyqtSignal
from qgis.PyQt.QtGui import QDesktopServices, QImage

from qgis.core import NULL, Qgis, QgsMapLayer, QgsMessageLog, QgsProject

from ..conf import DEBUG_MODE, PLUGIN_NAME


def logMessage(message, warning=False, error=False):
    """Log a message to the QGIS log message panel and also forward it to the web view if active.

    Args:
        message: The message to log.
        warning: If True, log at warning level.
        error: If True, log at error level.
    """
    if correspondent:
        if warning:
            level = "warn"
        elif error:
            level = "error"
        else:
            level = "debug"
        correspondent.messageSent.emit(message, level)

    level = Qgis.Critical if error else (Qgis.Warning if warning else Qgis.Info)
    QgsMessageLog.logMessage(str(message), PLUGIN_NAME, level, warning or error)


def qDebug(message):
    """Send a message to Qt's debug output.

    Args:
        message: The message to send.
    """
    qDebugA(message.encode("utf-8"))


### QGIS layer related functions ###
def getLayersInProject():
    """Return a list of layers available in the current QGIS project.

    Returns:
        list: A list of QgsMapLayer objects.
    """
    layers = []
    for tl in QgsProject.instance().layerTreeRoot().findLayers():
        if tl.layer():
            layers.append(tl.layer())
    return layers


def getDEMLayersInProject():
    """Return single-band GDAL raster layers (e.g. DEMs) from the project.

    Returns:
        list: Raster layers that match the criteria.
    """
    layers = []
    for layer in getLayersInProject():
        if layer.type() == QgsMapLayer.RasterLayer:
            if layer.providerType() == "gdal" and layer.bandCount() == 1:
                layers.append(layer)
    return layers


def getLayersByLayerIds(layerIds):
    """Return QgsMapLayer objects for the given layer IDs.

    Args:
        layerIds: A list of layer IDs.

    Returns:
        list: QgsMapLayer objects.
    """
    layers = []
    for id in layerIds:
        layer = QgsProject.instance().mapLayer(id)
        if layer:
            layers.append(layer)
    return layers


def shortTextFromSelectedLayerIds(layerIds):
    """Create a short textual description from selected layer IDs.

    Examples: "1 layer selected", "2 layers selected".

    Args:
        layerIds: List of layer IDs.

    Returns:
        str: Short English description.
    """
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


### JavaScript utility functions ###
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
        return "{}{:02x}{:02x}{:02x}".format(prefix, *c[:3])

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
    """Convert a Python object to a JavaScript literal representation.

    Args:
        obj: dict/list/str/bool/number/bytes/qgis.core.NULL etc.
        escape: Whether to escape strings and wrap them in double quotes.
        quoteHex: Whether to quote strings in '0x...' hex format.

    Returns:
        str or number: a JS literal representation.
    """
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
    """Converts the number to hex and maps 0-9 to a-j and a-f to k-p.

    Args:
        number: Integer value.

    Returns:
        str: Converted string.
    """
    h = ""
    for c in "{:x}".format(number):
        i = ord(c)
        if i >= 97:   # a - f => k - p
            h += chr(i + 10)
        else:         # 0 - 9 => a - j
            h += chr(i + 49)
    return h


def parseInt(string, def_val=None):
    try:
        return int(string)
    except (TypeError, ValueError):
        return def_val


def parseFloat(string, def_val=None):
    try:
        return float(string)
    except (TypeError, ValueError):
        return def_val


def image2dataUri(image, fmt="PNG"):
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, fmt.upper())
    return "data:image/{};base64,".format(fmt.lower()) + ba.toBase64().data().decode("ascii")


def base64file(file_path):
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except:
        logMessage("Cannot read file: {}".format(file_path), warning=True)
        return ""


def imageFile2dataUri(file_path):
    imgType = os.path.splitext(file_path)[1].lower()[1:].replace("jpg", "jpeg")
    return "data:image/{};base64,".format(imgType) + base64file(file_path)


def jpegCompressedImage(image):
    """Recreate a QImage compressed as JPEG."""
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPEG")

    return QImage.fromData(ba, "JPEG")


### File and directory related functions ###
def pluginDir(*subdirs):
    p = os.path.dirname(os.path.dirname(__file__))
    if subdirs:
        return os.path.join(p, *subdirs)
    return p


def templateDir():
    return pluginDir("web/html_templates")


def temporaryOutputDir():
    return QDir.tempPath() + "/Qgis2threejs"


def openDirectory(dir_path):
    """Open a directory in the OS default file manager."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))


def openUrl(url):
    """Open a URL using a configured browser if set, otherwise the default browser.

    Args:
        url: QUrl object.
    """
    if url.fileName().endswith((".html", ".htm")):
        settings = QSettings()
        browserPath = settings.value("/Qgis2threejs/browser", "", type=str)
        if browserPath:
            if QProcess.startDetached(browserPath, [url.toString()]):
                return
            else:
                logMessage("Incorrect web browser path. Open URL using default web browser.", warning=True)

    QDesktopServices.openUrl(url)


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
                filenames = QDir(source).entryList(QDir.Filter.Files)
                for filename in filenames:
                    copyFile(os.path.join(source, filename), os.path.join(dest, filename), overwrite)


def removeDir(dirName):
    d = QDir(dirName)
    if d.exists():
        for info in d.entryInfoList(QDir.Filter.Dirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot):
            if info.isDir():
                removeDir(info.absoluteFilePath())
            else:
                d.remove(info.fileName())
        d.rmdir(dirName)


def removeTemporaryFiles(filelist):
    """Remove a list of temporary files."""
    for file in filelist:
        QFile.remove(file)


def removeTemporaryOutputDir():
    removeDir(temporaryOutputDir())


def getTemplateConfig(template_path):
    """Read a template's .txt metadata file and return it as a dict.

    Args:
        template_path: Relative path to the template file.

    Returns:
        dict: Meta information (includes 'path' key with absolute template path).
    """
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


def settingsFilePath():
    """Return the export settings file path associated with the current project.

    Returns empty string if the project has not been saved yet.
    """
    proj_path = QgsProject.instance().fileName()
    return proj_path + ".qto3settings" if proj_path else ""


def createUid():
    """Generate a short unique id."""
    return QUuid.createUuid().toString()[1:9]


### Logging ###

class Logger(QObject):
    """Logs messages to the QGIS log message panel. Also emits a 'logged' signal when a message is
       logged, allowing it to be printed in the web view console.
    """

    logged = pyqtSignal(str, str)      # message, level

    def __init__(self, debug_mode=1, parent=None):
        QObject.__init__(self, parent)

        self.logfile = None
        if debug_mode == 2:
            self.logfile = open(pluginDir("qgis2threejs.log"), "w")

        else:
            self.log_to_file = self.do_nothing

            if debug_mode == 0:
                self.debug = self.do_nothing

    def info(self, msg):
        QgsMessageLog.logMessage(str(msg), tag=PLUGIN_NAME, level=Qgis.Info, notifyUser=False)
        self.logged.emit(msg, "info")
        self.log_to_file(msg, "info")

    def warning(self, msg):
        QgsMessageLog.logMessage(str(msg), tag=PLUGIN_NAME, level=Qgis.Warning, notifyUser=True)
        self.logged.emit(msg, "warn")
        self.log_to_file(msg, "warn")

    def error(self, msg):
        QgsMessageLog.logMessage(str(msg), tag=PLUGIN_NAME, level=Qgis.Critical, notifyUser=True)
        self.logged.emit(msg, "error")
        self.log_to_file(msg, "error")

    def debug(self, msg):
        QgsMessageLog.logMessage(str(msg), tag=PLUGIN_NAME, level=Qgis.Info, notifyUser=False)
        self.logged.emit(msg, "debug")
        self.log_to_file(msg, "debug")

    def log_to_file(self, msg, level=""):
        if not self.logfile:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.logfile.write("[{} - {}] {}\n".format(now, level, msg))
        self.logfile.flush()

    def do_nothing(self, msg, _=""):
        pass


logger = Logger(DEBUG_MODE)
