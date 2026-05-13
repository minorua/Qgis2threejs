# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2013-12-21

import os

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QAction, QActionGroup
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsApplication, QgsProject

from .utils.logging import configureLoggers, logger
configureLoggers()

from .conf import DEBUG_MODE, PLUGIN_NAME
from .core.exportsettings import ExportSettings
from .core.processing.procprovider import Qgis2threejsProvider
from .gui.webview.const import WebViewType, WebViewMode
from .gui.webview.webview import WEBENGINE_AVAILABLE, WEBENGINE_INPROCESS_WEBGL_AVAILABLE
from .gui.window import Q3DWindow
from .utils.basic import pluginDir
from .utils.file import removeTemporaryOutputDir
from .utils.qgis import settingsFilePath


class Qgis2threejs:

    LAST_ACTION = "/Qgis2threejs/lastAction"

    def __init__(self, iface):
        self.iface = iface
        self.pprovider = Qgis2threejsProvider()

        self.currentProjectPath = ""
        self.exportSettings = None
        self.liveExporter = None
        self.previewEnabled = True

    def initGui(self):
        # add a toolbar button
        icon = QIcon(pluginDir("Qgis2threejs.png"))
        title = "Qgis2threejs Exporter"
        wnd = self.iface.mainWindow()
        objName = "Qgis2threejsExporter"

        self.action = QAction(icon, title, wnd)
        self.action.setObjectName(objName)
        self.action.triggered.connect(self.openExporterLastAction)

        self.iface.addWebToolBarIcon(self.action)

        # web menu items
        self.actionGroup = QActionGroup(wnd)
        self.actionGroup.setObjectName(objName + "Group")

        if WEBENGINE_AVAILABLE:
            if WEBENGINE_INPROCESS_WEBGL_AVAILABLE:
                action = QAction(icon, title + " (Native)", self.actionGroup)
                action.setObjectName(objName + "WE")
                action.triggered.connect(lambda c, a=action: self.openExporterInProc(a))

            if os.name == "nt":
                action = QAction(icon, title + " (Embedded External)", self.actionGroup)
                action.setObjectName(objName + "Emb")
                action.triggered.connect(lambda c, a=action: self.openExporterEmbedded(a))

            action = QAction(icon, title + " (Separate External)", self.actionGroup)
            action.setObjectName(objName + "Sep")
            action.triggered.connect(lambda c, a=action: self.openExporerSeparate(a))

        action = QAction(icon, title + " (No Preview)", self.actionGroup)
        action.setObjectName(objName + "WoP")
        action.triggered.connect(lambda c, a=action: self.openExporerWithoutPreview(a))

        for action in self.actionGroup.actions():
            action.setCheckable(True)

            lastAction = QSettings().value(self.LAST_ACTION)
            if action.objectName() == lastAction:
                action.setChecked(True)

            self.iface.addPluginToWebMenu(PLUGIN_NAME, action)

        # connect signal-slot
        QgsProject.instance().removeAll.connect(self.allLayersRemoved)

        # register processing provider
        QgsApplication.processingRegistry().addProvider(self.pprovider)

    def unload(self):
        # disconnect signal-slot
        QgsProject.instance().removeAll.disconnect(self.allLayersRemoved)

        # remove the web menu items and icon
        self.action.triggered.disconnect(self.openExporterLastAction)
        self.iface.removeWebToolBarIcon(self.action)

        for action in self.actionGroup.actions():
            action.triggered.disconnect()
            self.iface.removePluginWebMenu(PLUGIN_NAME, action)

        # remove provider from processing registry
        QgsApplication.processingRegistry().removeProvider(self.pprovider)

        # temporary output directory
        removeTemporaryOutputDir()

    def openExporter(self, _=False, webViewType=WebViewType.WEBENGINE, webViewMode=WebViewMode.INPROCESS):
        if self.liveExporter:
            logger.info("Qgis2threejs Exporter is already open.")
            self.liveExporter.activateWindow()
            return

        needsToUpdateLayers = True
        proj_path = QgsProject.instance().fileName()
        if proj_path and proj_path != self.currentProjectPath:
            filepath = settingsFilePath()   # get settings file path for current project
            if os.path.exists(filepath):
                self.exportSettings = ExportSettings()
                self.exportSettings.loadSettingsFromFile(filepath)
                needsToUpdateLayers = False

        self.exportSettings = self.exportSettings or ExportSettings()
        self.exportSettings.isPreview = True
        self.exportSettings.requiresJsonSerializable = True
        self.exportSettings.setMapSettings(self.iface.mapCanvas().mapSettings())
        if needsToUpdateLayers:
            self.exportSettings.updateLayers()

        self.liveExporter = Q3DWindow(self.iface,
                                      self.exportSettings,
                                      webViewType=webViewType,
                                      webViewMode=webViewMode,
                                      previewEnabled=self.previewEnabled)
        self.liveExporter.show()
        self.liveExporter.previewEnabledChanged.connect(self.previewEnabledChanged)
        self.liveExporter.destroyed.connect(self.exporterDestroyed)

        self.currentProjectPath = proj_path

    def openExporterLastAction(self):
        lastAction = QSettings().value(self.LAST_ACTION)

        for action in self.actionGroup.actions():
            if action.objectName() == lastAction:
                action.triggered.emit()
                return

        if WEBENGINE_AVAILABLE:
            if os.name == "nt":
                self.openExporter(webViewMode=WebViewMode.EMBEDDED)
            else:
                self.openExporter(webViewMode=WebViewMode.SEPARATE)
        else:
            self.openExporter(webViewType=WebViewType.NONE)

    def openExporterInProc(self, action):
        self.openExporter(webViewMode=WebViewMode.INPROCESS)
        self.saveLastAction(action)

    def openExporterEmbedded(self, action):
        self.openExporter(webViewMode=WebViewMode.EMBEDDED)
        self.saveLastAction(action)

    def openExporerSeparate(self, action):
        self.openExporter(webViewMode=WebViewMode.SEPARATE)
        self.saveLastAction(action)

    def openExporerWithoutPreview(self, action):
        self.openExporter(webViewType=WebViewType.NONE)
        self.saveLastAction(action)

    def saveLastAction(self, action):
        QSettings().setValue(self.LAST_ACTION, action.objectName())

    def previewEnabledChanged(self, enabled):
        self.previewEnabled = enabled

    def exporterDestroyed(self, obj):
        if DEBUG_MODE:
            from .utils.debug import logReferenceCount
            logReferenceCount(self.liveExporter)

        self.liveExporter = None

    def allLayersRemoved(self):
        if self.liveExporter:
            return

        self.currentProjectPath = ""
        self.exportSettings = None
