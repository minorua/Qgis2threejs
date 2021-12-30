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
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot, qDebug
from qgis.core import QgsApplication

from .conf import DEBUG_MODE
from .build import ThreeJSBuilder
from .exportsettings import ExportSettings
from .q3dcore import Layer
from .q3dconst import LayerType, Script
from .tools import js_bool, logMessage


class Q3DControllerInterface(QObject):

    # signals
    dataReady = pyqtSignal(dict)                 # data
    scriptReady = pyqtSignal(str, object, str)   # script, data, msg_shown_in_log_panel
    messageReady = pyqtSignal(str, int, bool)    # message, timeout, show_in_msg_bar
    progressUpdated = pyqtSignal(int, str)
    loadScriptsRequest = pyqtSignal(list, bool)  # list of script ID, force (if False, do not load a script that is already loaded)

    def __init__(self, controller=None):
        super().__init__(parent=controller)

        self.controller = controller
        self.iface = None

    def connectToIface(self, iface):
        """iface: web view side interface (Q3DInterface or its subclass)"""
        self.iface = iface

        self.dataReady.connect(iface.loadJSONObject)
        self.scriptReady.connect(iface.runScript)
        self.loadScriptsRequest.connect(iface.loadScriptFiles)
        self.messageReady.connect(iface.showMessage)
        self.progressUpdated.connect(iface.progress)

        if hasattr(iface, "abortRequest"):
            iface.abortRequest.connect(self.controller.abort)
            iface.updateSceneRequest.connect(self.controller.requestSceneUpdate)
            iface.updateLayerRequest.connect(self.controller.requestLayerUpdate)
            iface.updateWidgetRequest.connect(self.controller.requestWidgetUpdate)
            iface.runScriptRequest.connect(self.controller.requestRunScript)

            iface.exportSettingsUpdated.connect(self.controller.exportSettingsUpdated)
            iface.cameraChanged.connect(self.controller.switchCamera)
            iface.navStateChanged.connect(self.controller.setNavigationEnabled)
            iface.previewStateChanged.connect(self.controller.setPreviewEnabled)
            iface.layerAdded.connect(self.controller.addLayer)
            iface.layerRemoved.connect(self.controller.removeLayer)

    def disconnectFromIface(self):
        self.dataReady.disconnect(self.iface.loadJSONObject)
        self.scriptReady.disconnect(self.iface.runScript)
        self.loadScriptsRequest.disconnect(self.iface.loadScriptFiles)
        self.messageReady.disconnect(self.iface.showMessage)
        self.progressUpdated.disconnect(self.iface.progress)

        if hasattr(self.iface, "abortRequest"):
            self.iface.abortRequest.disconnect(self.controller.abort)
            self.iface.updateSceneRequest.disconnect(self.controller.requestSceneUpdate)
            self.iface.updateLayerRequest.disconnect(self.controller.requestLayerUpdate)
            self.iface.updateWidgetRequest.disconnect(self.controller.requestWidgetUpdate)
            self.iface.runScriptRequest.disconnect(self.controller.requestRunScript)

            self.iface.exportSettingsUpdated.disconnect(self.controller.exportSettingsUpdated)
            self.iface.cameraChanged.disconnect(self.controller.switchCamera)
            self.iface.navStateChanged.disconnect(self.controller.setNavigationEnabled)
            self.iface.previewStateChanged.disconnect(self.controller.setPreviewEnabled)
            self.iface.layerAdded.disconnect(self.controller.addLayer)
            self.iface.layerRemoved.disconnect(self.controller.removeLayer)

        self.iface = None

    def loadJSONObject(self, obj):
        self.dataReady.emit(obj)

    def runScript(self, string, data=None, msg=""):
        self.scriptReady.emit(string, data, msg)

    def showMessage(self, msg, timeout=0):
        """show message in status bar. timeout: in milli-seconds"""
        self.messageReady.emit(msg, timeout, False)

    def clearMessage(self):
        """clear message in status bar"""
        self.messageReady.emit("", 0, False)

    def showMessageBar(self, msg="", timeout=10):
        """show message bar (error message only). timeout: in seconds"""
        msg = msg or "An error has occurred. See log messages panel for details."
        self.messageReady.emit(msg, timeout, True)

    def progress(self, percentage=100, msg=""):
        self.progressUpdated.emit(percentage, msg)

    def loadScriptFile(self, id, force=False):
        self.loadScriptsRequest.emit([id], force)

    def loadScriptFiles(self, ids, force=False):
        self.loadScriptsRequest.emit(ids, force)


class Q3DController(QObject):

    # requests
    BUILD_SCENE_ALL = 1   # build scene
    BUILD_SCENE = 2       # build scene, but do not update background color, coordinates display mode and so on
    RUN_SCRIPT = 3

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
        self.mapCanvas = None

        self.requestQueue = []
        self.timer = QTimer(self)
        self.timer.setInterval(1)
        self.timer.setSingleShot(True)

        # move to worker thread
        if thread:
            self.moveToThread(thread)

        self.timer.timeout.connect(self._processRequests)

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
        # self.mapCanvas.extentsChanged.connect(self.updateExtent)

    def disconnectFromMapCanvas(self):
        if self.mapCanvas:
            self.mapCanvas.renderComplete.disconnect(self._requestSceneUpdate)
            # self.mapCanvas.extentsChanged.disconnect(self.updateExtent)
            self.mapCanvas = None

    def buildScene(self, update_scene_opts=True, build_layers=True, update_extent=True, base64=False):
        if self.updating:
            logMessage("Previous building is still in progress. Cannot start to build scene.")
            return

        self.updating = True
        self.settings.base64 = base64

        self.iface.progress(0, "Updating scene")

        if update_extent and self.mapCanvas:
            self.builder.settings.setMapSettings(self.mapCanvas.mapSettings())

        self.iface.loadJSONObject(self.builder.buildScene(False))

        if update_scene_opts:
            sp = self.settings.sceneProperties()
            t, f = ("true", "false")

            # automatic z shift adjustment
            self.iface.runScript("Q3D.Config.autoZShift = {};".format(t if sp.get("checkBox_autoZShift") else f))

            # outline effect
            self.iface.runScript("setOutlineEffectEnabled({});".format(t if sp.get("checkBox_Outline") else f))

            # update background color
            params = "{0}, 1".format(sp.get("colorButton_Color", 0)) if sp.get("radioButton_Color") else "0, 0"
            self.iface.runScript("setBackgroundColor({0});".format(params))

            # coordinate display
            self.iface.runScript("Q3D.Config.coord.visible = {};".format(t if self.settings.coordDisplay() else f))

            latlon = self.settings.coordLatLon()
            self.iface.runScript("Q3D.Config.coord.latlon = {};".format(t if latlon else f))
            if latlon:
                self.iface.loadScriptFile(Script.PROJ4)

        if build_layers:
            self.buildLayers()

        self.updating = False
        self.updatingLayerId = None
        self.aborted = False
        self.iface.progress()
        self.iface.clearMessage()
        self.settings.base64 = False
        return True

    def buildLayers(self):
        self.iface.runScript('loadStart("LYRS", true);')

        layers = self.settings.getLayerList()
        for layer in sorted(layers, key=lambda lyr: lyr.type):
            if layer.visible:
                if not self._buildLayer(layer) or self.aborted:
                    break

        self.iface.runScript('loadEnd("LYRS");')

    def buildLayer(self, layer):
        if isinstance(layer, dict):
            layer = Layer.fromDict(layer)

        if self.updating:
            logMessage('Previous building is still in progress. Cannot start building layer "{}".'.format(layer.name))
            return False

        self.updating = True
        self.updatingLayerId = layer.layerId
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

        if layer.type == LayerType.POINT and layer.properties.get("comboBox_ObjectType") == "Model File":
            self.iface.loadScriptFiles([Script.COLLADALOADER,
                                        Script.GLTFLOADER])

        elif layer.type == LayerType.LINESTRING and layer.properties.get("comboBox_ObjectType") == "Thick Line":
            self.iface.loadScriptFiles([Script.MESHLINE])

        elif layer.type == LayerType.POINTCLOUD:
            self.iface.loadScriptFiles([Script.FETCH,
                                        Script.POTREE,
                                        Script.PCLAYER])

        t0 = t4 = time.time()
        dlist = []
        i = 0
        for builder in self.builder.layerBuilders(layer):
            self.iface.progress(i / (i + 4) * 100, pmsg)
            if self.aborted:
                self.iface.runScript("loadAborted();")
                logMessage("***** layer building aborted *****", False)
                return False

            t1 = time.time()
            obj = builder.build()
            t2 = time.time()

            if obj:
                self.iface.loadJSONObject(obj)

            QgsApplication.processEvents()      # NOTE: process events only for the calling thread
            i += 1

            t3 = time.time()
            dlist.append([t1 - t4, t2 - t1, t3 - t2])
            t4 = t3

        self.iface.runScript('loadEnd("L{}");'.format(layer.jsLayerId))

        if DEBUG_MODE:
            dlist = "\n".join([" {:.3f} {:.3f} {:.3f}".format(d[0], d[1], d[2]) for d in dlist])
            qDebug("{0} layer updated: {1:.3f}s\n{2}\n".format(layer.name,
                                                               time.time() - t0,
                                                               dlist).encode("utf-8"))
        return True

    def hideLayer(self, layer):
        """hide layer and remove all objects from the layer"""
        self.iface.runScript('hideLayer("{}", true)'.format(layer.jsLayerId))

    def hideAllLayers(self):
        """hide all layers and remove all objects from the layers"""
        self.iface.runScript("hideAllLayers(true)")

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
                self.buildScene(update_scene_opts=False)

            else:
                item = self.requestQueue.pop(0)
                if isinstance(item, Layer):
                    if item.visible:
                        self.buildLayer(item)
                    else:
                        self.hideLayer(item)
                else:
                    self.iface.runScript(item.get("string"), item.get("data"))

        except Exception as e:
            import traceback
            logMessage(traceback.format_exc())

            self.iface.showMessageBar()

        self.processRequests()

    @pyqtSlot(bool)
    def abort(self, clear_queue=True):
        if clear_queue:
            self.requestQueue.clear()

        if self.updating and not self.aborted:
            self.aborted = True
            self.iface.showMessage("Aborting processing...")

    @pyqtSlot(object, bool)
    def requestSceneUpdate(self, properties=0, update_all=True):
        if DEBUG_MODE:
            logMessage("Scene update was requested: {}".format(properties), False)

        if isinstance(properties, dict):
            self.settings.setSceneProperties(properties)

        self.requestQueue.append(self.BUILD_SCENE_ALL if update_all else self.BUILD_SCENE)

        if self.updating:
            self.abort(clear_queue=False)
        else:
            self.processRequests()

    @pyqtSlot(Layer)
    def requestLayerUpdate(self, layer):
        if DEBUG_MODE:
            logMessage("Layer update for {} was requested ({}).".format(layer.layerId, "visible" if layer.visible else "hidden"), False)

        # update layer properties and layer state in worker side export settings
        lyr = self.settings.getLayer(layer.layerId)
        if not lyr:
            return
        layer.copyTo(lyr)

        q = []
        for i in self.requestQueue:
            if isinstance(i, Layer) and i.layerId == layer.layerId:
                if not i.opt.onlyMaterial:
                    layer.opt.onlyMaterial = False
            else:
                q.append(i)

        self.requestQueue = q

        if self.updatingLayerId == layer.layerId:
            self.abort(clear_queue=False)

        if layer.visible:
            self.requestQueue.append(layer)

            if not self.updating:
                self.processRequests()

        else:
            # immediately hide layer without adding layer to queue
            self.hideLayer(layer)

    @pyqtSlot(str, dict)
    def requestWidgetUpdate(self, name, properties):
        if name == "NorthArrow":
            self.iface.runScript("setNorthArrowColor({0});".format(properties.get("color", 0)))
            self.iface.runScript("setNorthArrowVisible({0});".format(js_bool(properties.get("visible"))))

        elif name == "Label":
            self.iface.runScript('setHFLabel(fetchData());', data=properties)

        else:
            return

        self.settings.setWidgetProperties(name, properties)

    @pyqtSlot(str, object)
    def requestRunScript(self, string, data=None):
        self.requestQueue.append({"string": string, "data": data})

        if not self.updating:
            self.processRequests()

    @pyqtSlot(ExportSettings)
    def exportSettingsUpdated(self, settings):
        if self.updating:
            self.abort()

        self.hideAllLayers()
        settings.copyTo(self.settings)

        # camera
        self.switchCamera(self.settings.isOrthoCamera())

        # widgets
        for name in ExportSettings.WIDGET_LIST:
            self.requestWidgetUpdate(name, self.settings.widgetProperties(name))

        # scene
        self.requestSceneUpdate()

    @pyqtSlot(bool)
    def switchCamera(self, is_ortho=False):
        self.settings.setCamera(is_ortho)
        self.iface.runScript("switchCamera({0});".format(js_bool(is_ortho)))

    @pyqtSlot(bool)
    def setNavigationEnabled(self, enabled):
        self.settings.setNavigationEnabled(enabled)
        self.iface.runScript("setNavigationEnabled({0});".format(js_bool(enabled)))

    @pyqtSlot(bool)
    def setPreviewEnabled(self, enabled):
        self.enabled = enabled
        self.iface.runScript("setPreviewEnabled({});".format(js_bool(enabled)))

        if enabled:
            self.buildScene()
        else:
            self.abort()

    @pyqtSlot(Layer)
    def addLayer(self, layer):
        layer = self.settings.insertLayer(0, layer)
        self.buildLayer(layer)

    @pyqtSlot(str)
    def removeLayer(self, layerId):
        layer = self.settings.getLayer(layerId)
        if layer:
            self.hideLayer(layer)
            self.settings.removeLayer(layerId)

    # @pyqtSlot(QPainter)
    def _requestSceneUpdate(self, _=None):
        self.requestSceneUpdate(update_all=False)

    # @pyqtSlot()
    # def updateExtent(self):
    #     if self.settings.sceneProperties().get("radioButton_FixedExtent"):
    #         return
    #     self.requestQueue.clear()
    #     if self.updating:
    #         self.abort(clear_queue=False)


class Mock:

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        if DEBUG_MODE:
            logMessage("Mock: {}".format(attr), False)
        return Mock

    def __bool__(self):
        return False
