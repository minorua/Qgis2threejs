# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2013-12-21

import os

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QAction, QActionGroup
from PyQt5.QtGui import QIcon
from qgis.core import QgsApplication, QgsProject

from .conf import PLUGIN_NAME
from .exportsettings import ExportSettings
from .procprovider import Qgis2threejsProvider
from .utils import logMessage, pluginDir, removeTemporaryOutputDir, settingsFilePath
from .q3dwindow import Q3DWindow
from .q3dview import WEBENGINE_AVAILABLE, WEBKIT_AVAILABLE, WEBVIEWTYPE_NONE, WEBVIEWTYPE_WEBKIT, WEBVIEWTYPE_WEBENGINE, currentWebViewType


class Qgis2threejs:

    def __init__(self, iface):
        self.iface = iface
        self.pprovider = Qgis2threejsProvider()

        self.currentProjectPath = ""
        self.exportSettings = None
        self.liveExporter = None
        self.previewEnabled = True      # last preview state

    def initGui(self):
        # add a toolbar button and web menu items
        icon = QIcon(pluginDir("Qgis2threejs.png"))
        title = "Qgis2threejs Exporter"
        wnd = self.iface.mainWindow()
        objName = "Qgis2threejsExporter"

        self.action = QAction(icon, title, wnd)
        self.action.setObjectName(objName)
        self.action.triggered.connect(self.openExporter)

        self.iface.addWebToolBarIcon(self.action)

        self.actionGroup = QActionGroup(wnd)
        self.actionGroup.setObjectName(objName + "Group")

        if WEBENGINE_AVAILABLE:
            self.actionWebEng = QAction(icon, title + " (WebEngine)", self.actionGroup)
            self.actionWebEng.setObjectName(objName + "WebEng")
            self.actionWebEng.triggered.connect(self.openExporterWebEng)

            self.iface.addPluginToWebMenu(PLUGIN_NAME, self.actionWebEng)

        if WEBKIT_AVAILABLE:
            self.actionWebKit = QAction(icon, title + " (WebKit)", self.actionGroup)
            self.actionWebKit.setObjectName(objName + "WebKit")
            self.actionWebKit.triggered.connect(self.openExporterWebKit)

            self.iface.addPluginToWebMenu(PLUGIN_NAME, self.actionWebKit)

        if WEBENGINE_AVAILABLE and WEBKIT_AVAILABLE:
            self.actionWebEng.setCheckable(True)
            self.actionWebKit.setCheckable(True)

            if QSettings().value("/Qgis2threejs/preferWebKit", False):
                self.actionWebKit.setChecked(True)
            else:
                self.actionWebEng.setChecked(True)

        # connect signal-slot
        QgsProject.instance().removeAll.connect(self.allLayersRemoved)

        # register processing provider
        QgsApplication.processingRegistry().addProvider(self.pprovider)

    def unload(self):
        # disconnect signal-slot
        QgsProject.instance().removeAll.disconnect(self.allLayersRemoved)

        # remove the web menu items and icon
        self.action.triggered.disconnect(self.openExporter)
        self.iface.removeWebToolBarIcon(self.action)

        if WEBENGINE_AVAILABLE:
            self.actionWebEng.triggered.disconnect(self.openExporterWebEng)
            self.iface.removePluginWebMenu(PLUGIN_NAME, self.actionWebEng)

        if WEBKIT_AVAILABLE:
            self.actionWebKit.triggered.disconnect(self.openExporterWebKit)
            self.iface.removePluginWebMenu(PLUGIN_NAME, self.actionWebKit)

        # remove provider from processing registry
        QgsApplication.processingRegistry().removeProvider(self.pprovider)

        # remove temporary output directory
        removeTemporaryOutputDir()

    def openExporter(self, _=False, webViewType=None):
        """
        webViewType: WEBVIEWTYPE_NONE, WEBVIEWTYPE_WEBKIT, WEBVIEWTYPE_WEBENGINE or None. None means last used web view type.
        """
        if self.liveExporter:
            logMessage("Qgis2threejs Exporter is already open.", False)
            self.liveExporter.activateWindow()
            return

        layersUpdated = False
        proj_path = QgsProject.instance().fileName()
        if proj_path and proj_path != self.currentProjectPath:
            filepath = settingsFilePath()   # get settings file path for current project
            if os.path.exists(filepath):
                self.exportSettings = ExportSettings()
                self.exportSettings.loadSettingsFromFile(filepath)
                layersUpdated = True

        self.exportSettings = self.exportSettings or ExportSettings()
        if not layersUpdated:
            self.exportSettings.updateLayers()

        self.exportSettings.isPreview = True
        self.exportSettings.setMapSettings(self.iface.mapCanvas().mapSettings())

        logMessage("Opening Qgis2threejs Exporter...", False)
        self.liveExporter = Q3DWindow(self.iface,
                                      self.exportSettings,
                                      webViewType=webViewType,
                                      previewEnabled=self.previewEnabled)
        self.liveExporter.show()
        self.liveExporter.destroyed.connect(self.exporterDestroyed)

        self.currentProjectPath = proj_path

    def openExporterWebEng(self):
        self.openExporter(webViewType=WEBVIEWTYPE_WEBENGINE)

        QSettings().remove("/Qgis2threejs/preferWebKit")
        self.actionWebEng.setChecked(True)

    def openExporterWebKit(self):
        self.openExporter(webViewType=WEBVIEWTYPE_WEBKIT)

        if WEBENGINE_AVAILABLE:
            QSettings().setValue("/Qgis2threejs/preferWebKit", True)

        self.actionWebKit.setChecked(True)

    def exporterDestroyed(self, obj):
        if currentWebViewType != WEBVIEWTYPE_NONE:
            self.previewEnabled = self.liveExporter.controller.enabled      # remember preview state

        self.liveExporter = None

        logMessage("Qgis2threejs Exporter has closed.", False)

    def allLayersRemoved(self):
        self.currentProjectPath = ""
        self.exportSettings = None
