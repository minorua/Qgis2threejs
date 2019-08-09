# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DControllerLive

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
from PyQt5.QtCore import QTimer
from qgis.core import QgsApplication

from .conf import DEBUG_MODE
from .build import ThreeJSBuilder
from .exportsettings import ExportSettings, Layer
from .qgis2threejstools import logMessage, pluginDir


class Q3DController:

    # requests
    BUILD_SCENE_ALL = 1   # build scene
    BUILD_SCENE = 2       # build scene, but do not update background color, coordinates display mode and so on

    def __init__(self, qgis_iface=None, settings=None):
        self.qgis_iface = qgis_iface

        if settings is None:
            defaultSettings = {}
            settings = ExportSettings()
            settings.loadSettings(defaultSettings)
            if qgis_iface:
                settings.setMapCanvas(qgis_iface.mapCanvas())

            err_msg = settings.checkValidity()
            if err_msg:
                logMessage("Invalid settings: " + err_msg)

        self.settings = settings
        self.builder = ThreeJSBuilder(settings)

        self.iface = None
        self.enabled = True
        self.aborted = False  # layer export aborted
        self.updating = False
        self.layersNeedUpdate = False

        self.requestQueue = []
        self.timer = QTimer()
        self.timer.setInterval(1)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._processRequests)

        self.message1 = "Press ESC key to abort processing"

    def __del__(self):
        self.timer.stop()
        self.timer.deleteLater()

    def connectToIface(self, iface):
        """iface: Q3DViewerInterface"""
        self.iface = iface

    def disconnectFromIface(self):
        self.iface = Mock()

    def connectToMapCanvas(self):
        if self.qgis_iface:
            self.qgis_iface.mapCanvas().renderComplete.connect(self.requestSceneUpdate)
            self.qgis_iface.mapCanvas().extentsChanged.connect(self.updateExtent)

    def disconnectFromMapCanvas(self):
        if self.qgis_iface:
            self.qgis_iface.mapCanvas().renderComplete.disconnect(self.requestSceneUpdate)
            self.qgis_iface.mapCanvas().extentsChanged.disconnect(self.updateExtent)

    def abort(self):
        if self.updating and not self.aborted:
            self.aborted = True
            self.iface.runScript("loadAborted();")
            self.iface.showMessage("Aborting processing...")
            logMessage("***** scene/layer building aborted *****", False)

    def setPreviewEnabled(self, enabled):
        if not self.iface:
            return

        self.enabled = enabled
        self.iface.runScript("app.resume();" if enabled else "app.pause();");
        if enabled:
            self.buildScene()

    def buildScene(self, update_scene_all=True, build_layers=True, build_scene=True, update_extent=True, base64=False):
        if not (self.iface and self.enabled):
            return

        if self.updating:
            logMessage("Previous building is still in progress. Cannot start to build scene.")
            return

        self.updating = self.BUILD_SCENE_ALL if update_scene_all else self.BUILD_SCENE
        self.settings.base64 = base64
        self.layersNeedUpdate = self.layersNeedUpdate or build_layers

        self.iface.showMessage(self.message1)
        self.iface.progress(0, "Updating scene")

        if update_extent and self.qgis_iface:
            self.builder.settings.setMapCanvas(self.qgis_iface.mapCanvas())

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
            for idx, layer in enumerate(layers):
                self.iface.progress(idx / len(layers) * 100, "Updating layers")
                if layer.updated or (self.layersNeedUpdate and layer.visible):
                    if not self._buildLayer(layer) or self.aborted:
                        break
            self.iface.runScript('loadEnd("LYRS");')

            if not self.aborted:
                self.layersNeedUpdate = False

        self.updating = None
        self.aborted = False
        self.iface.progress()
        self.iface.clearMessage()
        self.settings.base64 = False
        return True

    def buildLayer(self, layer):
        if self.updating:
            logMessage('Previous building is still in progress. Cannot start to build layer "{}".'.format(layer.name))
            return False

        self.updating = layer
        self.iface.showMessage(self.message1)
        self.iface.progress(0, "Building {0}...".format(layer.name))
        self.iface.runScript('loadStart("LYR", true);')

        self._buildLayer(layer)

        self.iface.runScript('loadEnd("LYR");')
        self.updating = None
        self.aborted = False
        self.iface.progress()
        self.iface.clearMessage()
        return True

    def _buildLayer(self, layer):
        if not (self.iface and self.enabled) or self.aborted:
            return False

        self.iface.runScript('loadStart("L{}");  // {}'.format(layer.jsLayerId, layer.name))

        if layer.properties.get("comboBox_ObjectType") == "Model File":
            self.iface.loadModelLoaders()

        ts0 = time.time()
        tss = []
        for builder in self.builder.builders(layer):
            if self.aborted or not self.iface:
                return False
            ts1 = time.time()
            obj = builder.build()
            ts2 = time.time()
            self.iface.loadJSONObject(obj)
            ts3 = time.time()
            tss.append([ts2 - ts1, ts3 - ts2])
            QgsApplication.processEvents()      # NOTE: process events only for the calling thread

        layer.updated = False
        self.iface.runScript('loadEnd("L{}");'.format(layer.jsLayerId))

        if DEBUG_MODE:
            msg = "updating {0} costed {1:.3f}s:\n{2}".format(layer.name, time.time() - ts0, "\n".join(["{:.3f} {:.3f}".format(ts[0], ts[1]) for ts in tss]))
            logMessage(msg, False)
        return True

    def processRequests(self):
        self.timer.stop()
        if self.requestQueue:
            self.timer.start()

    def _processRequests(self):
        if self.updating or not self.requestQueue:
            return

        if self.BUILD_SCENE_ALL in self.requestQueue:
            self.requestQueue.clear()
            self.buildScene()

        elif self.BUILD_SCENE in self.requestQueue:
            self.requestQueue.clear()
            self.buildScene(update_scene_all=False)

        else:
            layer = self.requestQueue.pop(0)
            self.requestQueue = [i for i in self.requestQueue if i != layer]    # remove layer from queue
            self.buildLayer(layer)

        self.processRequests()

    def requestSceneUpdate(self, _=None, update_all=False):
        self.requestQueue.append(self.BUILD_SCENE_ALL if update_all else self.BUILD_SCENE)

        if self.updating:
            self.abort()
        else:
            self.processRequests()

    def requestLayerUpdate(self, layer):
        if not isinstance(layer, Layer):
            return

        self.requestQueue.append(layer)

        if self.updating == layer:
            self.abort()
        else:
            self.processRequests()

    def cancelLayerUpdateRequest(self, layer):
        if not isinstance(layer, Layer):
            return

        # remove layer from queue
        self.requestQueue = [i for i in self.requestQueue if i != layer]

        if self.updating == layer:
            self.abort()

    def updateExtent(self):
        self.layersNeedUpdate = True
        self.requestQueue.clear()
        if self.updating:
            self.abort()


class Mock:

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, attr):
        if DEBUG_MODE:
            logMessage("Mock: {}".format(attr), False)
        return Mock

    def __bool__(self):
        return False
