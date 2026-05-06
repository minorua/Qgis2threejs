# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2013-12-21

import os

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QAction, QActionGroup
from qgis.PyQt.QtGui import QIcon
from qgis.core import Qgis, QgsApplication, QgsProject

from .conf import DEBUG_MODE, PLUGIN_NAME
from .core.exportsettings import ExportSettings
from .core.processing.procprovider import Qgis2threejsProvider
from .gui.window import Q3DWindow
from .gui.webview import WEBENGINE_AVAILABLE, WEBENGINE_INPROCESS_WEBGL_AVAILABLE, WVM_INPROCESS, WVM_EMBEDDED_EXTERNAL, WVM_EXTERNAL_WINDOW
from .gui.webviewcommon import WEBVIEWTYPE_NONE, WEBVIEWTYPE_WEBENGINE
from .utils import logger, pluginDir, removeTemporaryOutputDir, settingsFilePath


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

        if WEBENGINE_INPROCESS_WEBGL_AVAILABLE:
            action = QAction(icon, title + " (In Process)", self.actionGroup)
            action.setObjectName(objName + "WebEng")
            action.triggered.connect(lambda c, a=action: self.openExporterWebEngInProc(a))

        action = QAction(icon, title + " (Embedded)", self.actionGroup)
        action.setObjectName(objName + "WebEngEE")
        action.triggered.connect(lambda c, a=action: self.openExporterEmbedded(a))

        action = QAction(icon, title + " (Floating)", self.actionGroup)
        action.setObjectName(objName + "WebEngEW")
        action.triggered.connect(lambda c, a=action: self.openExporerFloating(a))

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

    def openExporter(self, _=False, webViewType=None, webViewMode=None):
        """
        webViewType: WEBVIEWTYPE_NONE, WEBVIEWTYPE_WEBENGINE or None. None means last used web view type.
        """
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

        self.openExporter()

    def openExporterWebEngInProc(self, action):
        self.openExporter(webViewType=WEBVIEWTYPE_WEBENGINE, webViewMode=WVM_INPROCESS)
        self.saveLastAction(action)

    def openExporterEmbedded(self, action):
        self.openExporter(webViewType=WEBVIEWTYPE_WEBENGINE, webViewMode=WVM_EMBEDDED_EXTERNAL)
        self.saveLastAction(action)

    def openExporerFloating(self, action):
        self.openExporter(webViewType=WEBVIEWTYPE_WEBENGINE, webViewMode=WVM_EXTERNAL_WINDOW)
        self.saveLastAction(action)

    def openExporterWebEng(self, action):
        if WEBENGINE_AVAILABLE:
            self.openExporter(webViewType=WEBVIEWTYPE_WEBENGINE)
        else:
            self.openExporter(webViewType=WEBVIEWTYPE_NONE)
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
