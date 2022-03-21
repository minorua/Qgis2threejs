# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2013-12-21

import os

from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon
from qgis.core import QgsApplication, QgsProject

from .conf import PLUGIN_NAME
from .exportsettings import ExportSettings
from .procprovider import Qgis2threejsProvider
from .tools import logMessage, pluginDir, removeTemporaryOutputDir, settingsFilePath
from .q3dwindow import Q3DWindow


class Qgis2threejs:

    def __init__(self, iface):
        self.iface = iface
        self.pprovider = Qgis2threejsProvider()

        self.currentProjectPath = ""
        self.exportSettings = None
        self.liveExporter = None
        self.previewEnabled = True      # last preview state

    def initGui(self):
        # create actions
        icon = QIcon(pluginDir("Qgis2threejs.png"))
        self.action = QAction(icon, "Qgis2threejs Exporter", self.iface.mainWindow())
        self.action.setObjectName("Qgis2threejsExporter")
        self.actionNP = QAction(icon, "Qgis2threejs Exporter with Preview Off", self.iface.mainWindow())
        self.actionNP.setObjectName("Qgis2threejsExporterNoPreview")

        # add toolbar button and web menu items
        self.iface.addWebToolBarIcon(self.action)
        self.iface.addPluginToWebMenu(PLUGIN_NAME, self.action)
        self.iface.addPluginToWebMenu(PLUGIN_NAME, self.actionNP)

        # register processing provider
        QgsApplication.processingRegistry().addProvider(self.pprovider)

        # connect signal-slot
        self.action.triggered.connect(self.openExporter)
        self.actionNP.triggered.connect(self.openExporterWithPreviewDisabled)

        QgsProject.instance().removeAll.connect(self.allLayersRemoved)

    def unload(self):
        # disconnect signal-slot
        self.action.triggered.disconnect(self.openExporter)
        self.actionNP.triggered.disconnect(self.openExporterWithPreviewDisabled)

        QgsProject.instance().removeAll.disconnect(self.allLayersRemoved)

        # remove the web menu items and icon
        self.iface.removeWebToolBarIcon(self.action)
        self.iface.removePluginWebMenu(PLUGIN_NAME, self.action)
        self.iface.removePluginWebMenu(PLUGIN_NAME, self.actionNP)

        # remove provider from processing registry
        QgsApplication.processingRegistry().removeProvider(self.pprovider)

        # remove temporary output directory
        removeTemporaryOutputDir()

    def openExporter(self, _, no_preview=False):
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

        logMessage("Opening Qgis2threejs Exporter...", False)
        self.liveExporter = Q3DWindow(self.iface,
                                      self.exportSettings,
                                      preview=self.previewEnabled and not no_preview)
        self.liveExporter.show()
        self.liveExporter.destroyed.connect(self.exporterDestroyed)

        self.currentProjectPath = proj_path

    def openExporterWithPreviewDisabled(self):
        self.openExporter(False, True)

    def exporterDestroyed(self, obj):
        logMessage("Qgis2threejs Exporter has closed.", False)
        self.previewEnabled = self.liveExporter.controller.enabled      # remember preview state
        self.liveExporter = None

    def allLayersRemoved(self):
        self.currentProjectPath = ""
        self.exportSettings = None
