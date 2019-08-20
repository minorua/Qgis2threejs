# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DController

                              -------------------
        begin                : 2016-02-10
        copyright            : (C) 2016 Minoru Akagi
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
import time
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, qDebug
from qgis.core import QgsApplication

from .conf import DEBUG_MODE
from .build import ThreeJSBuilder
from .exportsettings import ExportSettings, Layer
from .qgis2threejstools import logMessage, pluginDir


class Q3DControllerInterface(QObject):

    # signals
    dataReady = pyqtSignal(dict)                # data
    scriptReady = pyqtSignal(str, str)          # script, msg_shown_in_log_panel
    messageReady = pyqtSignal(str, int, bool)        # message, timeout, show_in_msg_bar
    progressUpdated = pyqtSignal(int, str)
    loadScriptRequest = pyqtSignal(str)
    loadModelLoadersRequest = pyqtSignal()

    def __init__(self, controller=None):
        super().__init__(parent=controller)

        self.controller = controller
        self.iface = None

    def connectToIface(self, iface):
        """iface: web view side interface (Q3DInterface or its subclass)"""
        self.iface = iface

        self.dataReady.connect(iface.loadJSONObject)
        self.scriptReady.connect(iface.runScript)
        self.messageReady.connect(iface.showMessage)
        self.progressUpdated.connect(iface.progress)
        self.loadScriptRequest.connect(iface.loadScriptFile)
        self.loadModelLoadersRequest.connect(iface.loadModelLoaders)

        iface.updateSceneRequest.connect(self.controller.requestSceneUpdate)
        iface.updateLayerRequest.connect(self.controller.requestLayerUpdate)
        iface.clearSettingsRequest.connect(self.controller.clearExportSettings)
        iface.abortRequest.connect(self.controller.abort)
        iface.previewStateChanged.connect(self.controller.setPreviewEnabled)

    def disconnectFromIface(self):
        self.dataReady.disconnect(self.iface.loadJSONObject)
        self.scriptReady.disconnect(self.iface.runScript)
        self.messageReady.disconnect(self.iface.showMessage)
        self.progressUpdated.disconnect(self.iface.progress)
        self.loadScriptRequest.disconnect(self.iface.loadScriptFile)
        self.loadModelLoadersRequest.disconnect(self.iface.loadModelLoaders)

        self.iface.updateSceneRequest.disconnect(self.controller.requestSceneUpdate)
        self.iface.updateLayerRequest.disconnect(self.controller.requestLayerUpdate)
        self.iface.clearSettingsRequest.disconnect(self.controller.clearExportSettings)
        self.iface.abortRequest.disconnect(self.controller.abort)
        self.iface.previewStateChanged.disconnect(self.controller.setPreviewEnabled)
        self.iface = None

    def loadJSONObject(self, obj):
        self.dataReady.emit(obj)

    def runScript(self, script, msg=""):
        self.scriptReady.emit(script, msg)

    def showMessage(self, msg, timeout=0):
        """show message in status bar. timeout: in milli-seconds"""
        self.messageReady.emit(msg, timeout, False)

    def clearMessage(self):
        """clear message in status bar"""
        self.messageReady.emit("", 0, False)

    def showMessageBar(self, msg="", timeout=10):
        """show message bar (error message only). timeout: in seconds"""
        msg = msg or "An error has occurred. See message log (Qgis2threejs) for more details."
        self.messageReady.emit(msg, timeout, True)

    def progress(self, percentage=100, text=""):
        self.progressUpdated.emit(percentage, text)

    def loadScriptFile(self, filepath):
        self.loadScriptRequest.emit(filepath)

    def loadModelLoaders(self):
        self.loadModelLoadersRequest.emit()


class Q3DController(QObject):

    # requests
    BUILD_SCENE_ALL = 1   # build scene
    BUILD_SCENE = 2       # build scene, but do not update background color, coordinates display mode and so on

    def __init__(self, settings=None, thread=None, parent=None):
        super().__init__(parent)

        if settings is None:
            defaultSettings = {}
            settings = ExportSettings()
            settings.loadSettings(defaultSettings)

            err_msg = settings.checkValidity()
            if err_msg:
                logMessage("Invalid settings: " + err_msg)

        self.settings = settings
        self.builder = ThreeJSBuilder(settings)

        self.iface = Q3DControllerInterface(self)
        self.enabled = True
        self.aborted = False  # layer export aborted
        self.updating = False
        self.updatingLayerId = None
        self.layersNeedUpdate = False
        self.mapCanvas = None

        self.requestQueue = []
        self.timer = QTimer(self)
        self.timer.setInterval(1)
        self.timer.setSingleShot(True)

        # move to worker thread
        if thread:
            self.moveToThread(thread)

        self.timer.timeout.connect(self._processRequests)

        self.MSG1 = "Press ESC key to abort processing"

    def __del__(self):
        self.timer.stop()

    def connectToIface(self, iface):
        """iface: Q3DInterface or its subclass"""
        self.iface.connectToIface(iface)

    def disconnectFromIface(self):
        self.iface.disconnectFromIface()
        # self.iface = Mock()

    def connectToMapCanvas(self, canvas):
        self.mapCanvas = canvas
        self.mapCanvas.renderComplete.connect(self._requestSceneUpdate)
        self.mapCanvas.extentsChanged.connect(self.updateExtent)

    def disconnectFromMapCanvas(self):
        if self.mapCanvas:
            self.mapCanvas.renderComplete.disconnect(self._requestSceneUpdate)
            self.mapCanvas.extentsChanged.disconnect(self.updateExtent)
            self.mapCanvas = None

    def abort(self, clear_queue=True):
        if clear_queue:
            self.requestQueue.clear()

        if self.updating and not self.aborted:
            self.aborted = True
            self.iface.showMessage("Aborting processing...")

    def setPreviewEnabled(self, enabled):
        self.enabled = enabled
        self.iface.runScript("app.resume();" if enabled else "app.pause();")

        elem = "document.getElementById('cover')"
        self.iface.runScript("{}.style.display = '{}';".format(elem, "none" if enabled else "block"))
        if not enabled:
            self.iface.runScript("{}.innerHTML = '<img src=\"../Qgis2threejs.png\">';".format(elem))
            self.abort()
        else:
            self.buildScene()

    def buildScene(self, update_scene_all=True, build_layers=True, build_scene=True, update_extent=True, base64=False):
        if self.updating:
            logMessage("Previous building is still in progress. Cannot start to build scene.")
            return

        self.updating = True
        self.settings.base64 = base64
        self.layersNeedUpdate = self.layersNeedUpdate or build_layers

        self.iface.showMessage(self.MSG1)
        self.iface.progress(0, "Updating scene")

        if update_extent and self.mapCanvas:
            self.builder.settings.setMapSettings(self.mapCanvas.mapSettings())

        if build_scene:
            self.iface.loadJSONObject(self.builder.buildScene(False))

        if update_scene_all:
            sp = self.settings.sceneProperties()
            # automatic z shift adjustment
            self.iface.runScript("Q3D.Config.autoZShift = {};".format("true" if sp.get("checkBox_autoZShift") else "false"))

            # update background color
            params = "{0}, 1".format(sp.get("colorButton_Color", 0)) if sp.get("radioButton_Color") else "0, 0"
            self.iface.runScript("setBackgroundColor({0});".format(params))

            # coordinate display (geographic/projected)
            if sp.get("radioButton_WGS84", False):
                self.iface.loadScriptFile(pluginDir("js/proj4js/proj4.js"))
            else:
                self.iface.runScript("proj4 = undefined;", "// proj4 not enabled")

        if build_layers:
            self.iface.runScript('loadStart("LYRS", true);')

            layers = self.settings.getLayerList()
            for layer in sorted(layers, key=lambda lyr: lyr.geomType):
                if layer.updated or (self.layersNeedUpdate and layer.visible):
                    ret = self._buildLayer(layer)
                    if not ret or self.aborted:
                        break
            self.iface.runScript('loadEnd("LYRS");')

            if not self.aborted:
                self.layersNeedUpdate = False

        self.updating = False
        self.updatingLayerId = None
        self.aborted = False
        self.iface.progress()
        self.iface.clearMessage()
        self.settings.base64 = False
        return True

    def buildLayer(self, layer):
        if isinstance(layer, dict):
            layer = Layer.fromDict(layer)

        if self.updating:
            logMessage('Previous building is still in progress. Cannot start building layer "{}".'.format(layer.name))
            return False

        self.updating = True
        self.updatingLayerId = layer.layerId
        self.iface.showMessage(self.MSG1)
        self.iface.runScript('loadStart("LYR", true);')

        aborted = self._buildLayer(layer)

        self.iface.runScript('loadEnd("LYR");')
        self.updating = False
        self.updatingLayerId = None
        self.aborted = False
        self.iface.progress()
        self.iface.clearMessage()

        return aborted

    def _buildLayer(self, layer):
        self.iface.runScript('loadStart("L{}");  // {}'.format(layer.jsLayerId, layer.name))
        pmsg = "Building {0}...".format(layer.name)
        self.iface.progress(0, pmsg)

        if layer.properties.get("comboBox_ObjectType") == "Model File":
            self.iface.loadModelLoaders()   # need to load model loaders synchronously

        t0 = t4 = time.time()
        dlist = []
        i = 0
        for builder in self.builder.builders(layer):
            self.iface.progress(i / (i + 4) * 100, pmsg)
            if self.aborted:
                self.iface.runScript("loadAborted();")
                logMessage("***** layer building aborted *****", False)
                return False

            t1 = time.time()
            obj = builder.build()
            t2 = time.time()

            self.iface.loadJSONObject(obj)
            QgsApplication.processEvents()      # NOTE: process events only for the calling thread
            i += 1

            t3 = time.time()
            dlist.append([t1 - t4, t2 - t1, t3 - t2])
            t4 = t3

        layer.updated = False

        self.iface.runScript('loadEnd("L{}");'.format(layer.jsLayerId))

        if DEBUG_MODE:
            dlist = "\n".join([" {:.3f} {:.3f} {:.3f}".format(d[0], d[1], d[2]) for d in dlist])
            qDebug("{0} layer updated: {1:.3f}s\n{2}\n".format(layer.name,
                                                               time.time() - t0,
                                                               dlist).encode("utf-8"))
        return True

    def hideLayer(self, layer):
        """hide layer and remove all objects from the layer"""
        self.iface.runScript('hideLayer("{}", true)'.format(layer.jsLayerId));

    def hideAllLayers(self):
        """hide all layers and remove all objects from the layers"""
        self.iface.runScript("hideAllLayers(true)");

    def processRequests(self):
        self.timer.stop()
        if self.requestQueue:
            self.timer.start()

    def _processRequests(self):
        if not self.enabled or self.updating or not self.requestQueue:
            return

        try:
            if self.BUILD_SCENE_ALL in self.requestQueue:
                self.requestQueue.clear()
                self.buildScene()

            elif self.BUILD_SCENE in self.requestQueue:
                self.requestQueue.clear()
                self.buildScene(update_scene_all=False)

            else:
                layer = self.requestQueue.pop(0)
                if layer.visible:
                    self.buildLayer(layer)
                else:
                    self.hideLayer(layer)

        except Exception as e:
            import traceback
            logMessage(traceback.format_exc())

            self.iface.showMessageBar()

        self.processRequests()

    def requestSceneUpdate(self, properties=0, update_all=True):
        if DEBUG_MODE:
            logMessage("Scene update was requested: {}".format(properties))

        if isinstance(properties, dict):
            self.settings.setSceneProperties(properties)

        self.requestQueue.append(self.BUILD_SCENE_ALL if update_all else self.BUILD_SCENE)

        if self.updating:
            self.abort(clear_queue=False)
        else:
            self.processRequests()

    def requestLayerUpdate(self, layer):
        if DEBUG_MODE:
            logMessage("Layer update for {} was requested.".format(layer.layerId))

        # update layer properties and its state in export settings
        lyr = self.settings.getItemByLayerId(layer.layerId)
        if lyr is None:
            return

        layer.copyTo(lyr)

        self.requestQueue = [i for i in self.requestQueue if i.layerId != layer.layerId]

        if self.updatingLayerId == layer.layerId:
            self.requestQueue.append(layer)
            self.abort(clear_queue=False)

        elif layer.visible:
            self.requestQueue.append(layer)

            if not self.updating:
                self.processRequests()

        else:
            # immediately hide the layer
            self.hideLayer(layer)

    def clearExportSettings(self):
        self.settings.clear()
        self.settings.updateLayerList()
        self.requestSceneUpdate()
        self.hideAllLayers()

    def _requestSceneUpdate(self, _=None):
        self.requestSceneUpdate(update_all=False)

    def updateExtent(self):
        self.layersNeedUpdate = True
        self.requestQueue.clear()
        if self.updating:
            self.abort(clear_queue=False)


class Mock:

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        if DEBUG_MODE:
            logMessage("Mock: {}".format(attr), False)
        return Mock

    def __bool__(self):
        return False
