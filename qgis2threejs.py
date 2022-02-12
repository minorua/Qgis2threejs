# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2013-12-21

from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon

from qgis.core import QgsApplication, QgsProject

from .exportsettings import ExportSettings
from .procprovider import Qgis2threejsProvider
from .tools import logMessage, pluginDir, removeTemporaryOutputDir
from .q3dwindow import Q3DWindow


class Qgis2threejs:

    def __init__(self, iface):
        self.iface = iface
        self.pprovider = Qgis2threejsProvider()

        self.currentProjectPath = None
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

        # connect the actions
        self.action.triggered.connect(self.openExporter)
        self.actionNP.triggered.connect(self.openExporterWithPreviewDisabled)

        # add toolbar button and web menu items
        name = "Qgis2threejs"
        self.iface.addWebToolBarIcon(self.action)
        self.iface.addPluginToWebMenu(name, self.action)
        self.iface.addPluginToWebMenu(name, self.actionNP)

        # register processing provider
        QgsApplication.processingRegistry().addProvider(self.pprovider)

    def unload(self):
        # remove the web menu items and icon
        name = "Qgis2threejs"
        self.iface.removeWebToolBarIcon(self.action)
        self.iface.removePluginWebMenu(name, self.action)
        self.iface.removePluginWebMenu(name, self.actionNP)

        # remove provider from processing registry
        QgsApplication.processingRegistry().removeProvider(self.pprovider)

        # remove temporary output directory
        removeTemporaryOutputDir()

    def openExporter(self, _, no_preview=False):
        if self.liveExporter:
            logMessage("Qgis2threejs Exporter is already open.", False)
            self.liveExporter.activateWindow()
            return

        proj_path = QgsProject.instance().fileName()
        if proj_path != self.currentProjectPath:
            self.exportSettings = ExportSettings()
            self.exportSettings.loadSettingsFromFile()   # load export settings from settings file for current project
            self.currentProjectPath = proj_path

        else:
            self.exportSettings = self.exportSettings or ExportSettings()
            self.exportSettings.updateLayers()

        self.exportSettings.isPreview = True

        logMessage("Opening Qgis2threejs Exporter...", False)
        self.liveExporter = Q3DWindow(self.iface,
                                      self.exportSettings,
                                      preview=self.previewEnabled and not no_preview)
        self.liveExporter.show()
        self.liveExporter.destroyed.connect(self.exporterDestroyed)

    def openExporterWithPreviewDisabled(self):
        self.openExporter(False, True)

    def exporterDestroyed(self, obj):
        logMessage("Qgis2threejs Exporter has closed.", False)
        self.previewEnabled = self.liveExporter.controller.enabled      # remember preview state
        self.liveExporter = None
