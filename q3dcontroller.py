# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import time
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, pyqtSlot, qDebug
from qgis.core import QgsApplication

from .conf import DEBUG_MODE
from .build import ThreeJSBuilder
from .exportsettings import ExportSettings
from .q3dcore import Layer
from .q3dconst import LayerType, Script
from .utils import hex_color, js_bool, logMessage


class Q3DControllerInterface(QObject):

    # signals - controller iface to viewer iface
    dataSent = pyqtSignal(dict)                  # data
    scriptSent = pyqtSignal(str, object, str)    # script, data, msg_shown_in_log_panel
    statusMessage = pyqtSignal(str, int)         # message, timeout_ms
    progressUpdated = pyqtSignal(int, str)       # percentage, msg
    loadScriptsRequest = pyqtSignal(list, bool)  # list of script ID, force (if False, do not load a script that is already loaded)
    readyToQuit = pyqtSignal()

    def __init__(self, controller=None):
        super().__init__(parent=controller)

        self.controller = controller
        self.iface = None

    def connectToIface(self, iface):
        """iface: web view side interface (Q3DInterface or its subclass)"""
        self.iface = iface

        self.dataSent.connect(iface.sendJSONObject)
        self.scriptSent.connect(iface.runScript)
        self.loadScriptsRequest.connect(iface.loadScriptFiles)
        self.statusMessage.connect(iface.statusMessage)
        self.progressUpdated.connect(iface.progressUpdated)

        if hasattr(iface, "abortRequest"):
            iface.abortRequest.connect(self.controller.abort)
            iface.buildSceneRequest.connect(self.controller.requestBuildScene)
            iface.buildLayerRequest.connect(self.controller.requestBuildLayer)
            iface.updateWidgetRequest.connect(self.controller.requestUpdateWidget)
            iface.runScriptRequest.connect(self.controller.requestRunScript)

            iface.updateExportSettingsRequest.connect(self.controller.updateExportSettings)
            iface.cameraChanged.connect(self.controller.switchCamera)
            iface.navStateChanged.connect(self.controller.setNavigationEnabled)
            iface.previewStateChanged.connect(self.controller.setPreviewEnabled)
            iface.layerAdded.connect(self.controller.addLayer)
            iface.layerRemoved.connect(self.controller.removeLayer)

    def disconnectFromIface(self):
        iface = self.iface

        self.dataSent.disconnect(iface.sendJSONObject)
        self.scriptSent.disconnect(iface.runScript)
        self.loadScriptsRequest.disconnect(iface.loadScriptFiles)
        self.statusMessage.disconnect(iface.statusMessage)
        self.progressUpdated.disconnect(iface.progressUpdated)

        if hasattr(iface, "abortRequest"):
            iface.abortRequest.disconnect(self.controller.abort)
            iface.buildSceneRequest.disconnect(self.controller.requestBuildScene)
            iface.buildLayerRequest.disconnect(self.controller.requestBuildLayer)
            iface.updateWidgetRequest.disconnect(self.controller.requestUpdateWidget)
            iface.runScriptRequest.disconnect(self.controller.requestRunScript)

            iface.updateExportSettingsRequest.disconnect(self.controller.updateExportSettings)
            iface.cameraChanged.disconnect(self.controller.switchCamera)
            iface.navStateChanged.disconnect(self.controller.setNavigationEnabled)
            iface.previewStateChanged.disconnect(self.controller.setPreviewEnabled)
            iface.layerAdded.disconnect(self.controller.addLayer)
            iface.layerRemoved.disconnect(self.controller.removeLayer)

        self.iface = None

    def sendJSONObject(self, obj):
        self.dataSent.emit(obj)

    def runScript(self, string, data=None, msg=""):
        self.scriptSent.emit(string, data, msg)

    def showStatusMessage(self, msg, timeout_ms=0):
        """show message in status bar"""
        self.statusMessage.emit(msg, timeout_ms)

    def clearStatusMessage(self):
        """clear message in status bar"""
        self.statusMessage.emit("", 0)

    def showMessageBar(self, msg, timeout_ms=0, warning=False):
        """show message bar at top of web view"""
        self.runScript("showMessageBar(pyData(), {}, {})".format(timeout_ms, js_bool(warning)), data=msg)

    def progress(self, percentage=100, msg=""):
        self.progressUpdated.emit(int(percentage), msg)

    def loadScriptFile(self, id, force=False):
        self.loadScriptsRequest.emit([id], force)

    def loadScriptFiles(self, ids, force=False):
        self.loadScriptsRequest.emit(ids, force)


class Q3DController(QObject):

    # requests
    BUILD_SCENE_ALL = 1   # build scene
    BUILD_SCENE = 2       # build scene, but do not update background color, coordinates display mode and so on
    RELOAD_PAGE = 3

    def __init__(self, settings=None, thread=None, parent=None):
        super().__init__(parent)

        if settings is None:
            defaultSettings = {}
            settings = ExportSettings()
            settings.loadSettings(defaultSettings)

            err_msg = settings.checkValidity()
            if err_msg:
                logMessage("Invalid settings: " + err_msg, warning=True)

        self.settings = settings
        self.builder = ThreeJSBuilder(settings)

        self.iface = Q3DControllerInterface(self)
        self.iface.setObjectName("controllerInterface")

        self.enabled = True
        self.aborted = False  # layer export aborted
        self.processingLayer = None
        self.mapCanvas = None

        self.requestQueue = []
        self.timer = QTimer(self)
        self.timer.setInterval(1)
        self.timer.setSingleShot(True)

        # move to worker thread
        if thread:
            self.moveToThread(thread)

        self.timer.timeout.connect(self._processRequests)

    def teardown(self):
        self.timer.stop()
        self.timer.timeout.disconnect(self._processRequests)

        self.iface.deleteLater()
        self.iface = None

    def connectToIface(self, iface):
        """iface: Q3DInterface or its subclass"""
        self.iface.connectToIface(iface)

    def disconnectFromIface(self):
        self.iface.disconnectFromIface()
        # self.iface = Mock()

    def connectToMapCanvas(self, canvas):
        self.mapCanvas = canvas
        self.mapCanvas.renderComplete.connect(self._requestBuildScene)
        # self.mapCanvas.extentsChanged.connect(self.updateExtent)

    def disconnectFromMapCanvas(self):
        if self.mapCanvas:
            self.mapCanvas.renderComplete.disconnect(self._requestBuildScene)
            # self.mapCanvas.extentsChanged.disconnect(self.updateExtent)
            self.mapCanvas = None

    def buildScene(self, update_scene_opts=True, build_layers=True, update_extent=True):
        if self.processingLayer:
            logMessage("Previous processing is still in progress. Cannot start to build scene.")
            return False

        self.aborted = False

        self.iface.progress(0, "Building scene")

        if update_extent and self.mapCanvas:
            self.builder.settings.setMapSettings(self.mapCanvas.mapSettings())

        self.iface.sendJSONObject(self.builder.buildScene(False))

        if update_scene_opts:
            sp = self.settings.sceneProperties()

            # outline effect
            self.iface.runScript("setOutlineEffectEnabled({})".format(js_bool(sp.get("checkBox_Outline"))))

            # update background color
            params = "{0}, 1".format(hex_color(sp.get("colorButton_Color", 0), prefix="0x")) if sp.get("radioButton_Color") else "0, 0"
            self.iface.runScript("setBackgroundColor({0})".format(params))

            # coordinate display
            self.iface.runScript("Q3D.Config.coord.visible = {};".format(js_bool(self.settings.coordDisplay())))

            latlon = self.settings.isCoordLatLon()
            self.iface.runScript("Q3D.Config.coord.latlon = {};".format(js_bool(latlon)))
            if latlon:
                self.iface.loadScriptFile(Script.PROJ4)

        if build_layers:
            self.buildLayers()

        self.iface.progress()
        self.iface.clearStatusMessage()
        return not self.aborted

    def buildLayers(self):
        self.aborted = False
        self.iface.runScript('loadStart("LYRS", true)')

        ret = True
        layers = self.settings.layers()
        for layer in sorted(layers, key=lambda lyr: lyr.type):
            if layer.visible:
                if not self._buildLayer(layer) or self.aborted:
                    ret = False
                    break

        self.iface.runScript('loadEnd("LYRS")')
        return ret

    def buildLayer(self, layer):
        self.aborted = False
        if isinstance(layer, dict):
            layer = Layer.fromDict(layer)

        if self.processingLayer:
            logMessage('Previous processing is still in progress. Cannot start to build layer "{}".'.format(layer.name))
            return False

        ret = self._buildLayer(layer)

        self.iface.progress()
        self.iface.clearStatusMessage()

        if ret and len(self.settings.layersToExport()) == 1:
            self.iface.runScript("adjustCameraPos()")

        return ret

    def _buildLayer(self, layer):
        self.processingLayer = layer

        pmsg = "Building {0}...".format(layer.name)
        self.iface.progress(0, pmsg)

        if layer.type == LayerType.POINT and layer.properties.get("comboBox_ObjectType") == "3D Model":
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
                logMessage("***** layer processing aborted *****")
                self.processingLayer = None
                return False

            t1 = time.time()
            obj = builder.build()
            t2 = time.time()

            if obj:
                self.iface.sendJSONObject(obj)

            QgsApplication.processEvents()      # NOTE: process events only for the calling thread
            i += 1

            t3 = time.time()
            dlist.append([t1 - t4, t2 - t1, t3 - t2])
            t4 = t3

        if DEBUG_MODE:
            dlist = "\n".join([" {:.3f} {:.3f} {:.3f}".format(d[0], d[1], d[2]) for d in dlist])
            qDebug("{0} layer updated: {1:.3f}s\n{2}\n".format(layer.name,
                                                               time.time() - t0,
                                                               dlist).encode("utf-8"))
        self.processingLayer = None
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
        if not self.enabled or self.processingLayer or not self.requestQueue:
            return

        try:
            if self.BUILD_SCENE_ALL in self.requestQueue:
                self.requestQueue.clear()
                self.buildScene()

            elif self.BUILD_SCENE in self.requestQueue:
                self.requestQueue.clear()
                self.buildScene(update_scene_opts=False)

            elif self.RELOAD_PAGE in self.requestQueue:
                self.requestQueue.clear()
                self.iface.runScript("location.reload()")

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
            logMessage(traceback.format_exc(), warning=True)

            self.iface.showMessageBar("One or more errors occurred. See log messages panel in QGIS main window for details.", warning=True)

        self.processRequests()

    @pyqtSlot(bool)
    def abort(self, clear_queue=True):
        if clear_queue:
            self.requestQueue.clear()

        if not self.aborted:
            self.aborted = True
            self.iface.showStatusMessage("Aborting processing...")

    @pyqtSlot()
    def quit(self):
        self.abort()
        self.iface.readyToQuit.emit()
        self.teardown()

    @pyqtSlot(object, bool, bool)
    def requestBuildScene(self, properties=None, update_all=True, reload=False):
        if DEBUG_MODE:
            logMessage("Scene update requested: {}".format(properties))

        if properties:
            self.settings.setSceneProperties(properties)

        if reload:
            r = self.RELOAD_PAGE
        elif update_all:
            r = self.BUILD_SCENE_ALL
        else:
            r = self.BUILD_SCENE

        self.requestQueue.append(r)

        if self.processingLayer:
            self.abort(clear_queue=False)
        else:
            self.processRequests()

    @pyqtSlot(Layer)
    def requestBuildLayer(self, layer):
        if DEBUG_MODE:
            logMessage("Layer update for {} requested ({}).".format(layer.layerId, "visible" if layer.visible else "hidden"))

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

        if self.processingLayer and self.processingLayer.layerId == layer.layerId:
            self.abort(clear_queue=False)
            if not self.processingLayer.opt.onlyMaterial:
                layer.opt.onlyMaterial = False

        if layer.visible:
            self.requestQueue.append(layer)

            if not self.processingLayer:
                self.processRequests()
        else:
            # immediately hide layer without adding layer to queue
            self.hideLayer(layer)

    @pyqtSlot(str, dict)
    def requestUpdateWidget(self, name, properties):
        if name == "NorthArrow":
            self.iface.runScript("setNorthArrowColor({0})".format(properties.get("color", 0)))
            self.iface.runScript("setNorthArrowVisible({0})".format(js_bool(properties.get("visible"))))

        elif name == "Label":
            self.iface.runScript('setHFLabel(pyData());', data=properties)

        else:
            return

        self.settings.setWidgetProperties(name, properties)

    @pyqtSlot(str, object)
    def requestRunScript(self, string, data=None):
        self.requestQueue.append({"string": string, "data": data})

        if not self.processingLayer:
            self.processRequests()

    @pyqtSlot(ExportSettings)
    def updateExportSettings(self, settings):
        if self.processingLayer:
            self.abort()

        self.hideAllLayers()
        settings.copyTo(self.settings)

        # reload page
        self.iface.runScript("location.reload()")

    @pyqtSlot(bool)
    def switchCamera(self, is_ortho=False):
        self.settings.setCamera(is_ortho)
        self.iface.runScript("switchCamera({0})".format(js_bool(is_ortho)))

    @pyqtSlot(bool)
    def setNavigationEnabled(self, enabled):
        self.settings.setNavigationEnabled(enabled)
        self.iface.runScript("setNavigationEnabled({0})".format(js_bool(enabled)))

    @pyqtSlot(bool)
    def setPreviewEnabled(self, enabled):
        self.enabled = enabled
        self.iface.runScript("setPreviewEnabled({})".format(js_bool(enabled)))

        if enabled:
            self.buildScene()
        else:
            self.abort()

    @pyqtSlot(Layer)
    def addLayer(self, layer):
        layer = self.settings.addLayer(layer)
        self.buildLayer(layer)

    @pyqtSlot(str)
    def removeLayer(self, layerId):
        layer = self.settings.getLayer(layerId)
        if layer:
            self.hideLayer(layer)
            self.settings.removeLayer(layerId)

    # @pyqtSlot(QPainter)
    def _requestBuildScene(self, _=None):
        self.requestBuildScene(update_all=False)

    # @pyqtSlot()
    # def updateExtent(self):
    #     if self.settings.sceneProperties().get("radioButton_FixedExtent"):
    #         return
    #     self.requestQueue.clear()
    #     if self.processingLayer:
    #         self.abort(clear_queue=False)


class Mock:

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        if DEBUG_MODE:
            logMessage("Mock: {}".format(attr))
        return Mock

    def __bool__(self):
        return False
