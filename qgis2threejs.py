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
from .gui.webview import WEBENGINE_AVAILABLE, WEBKIT_AVAILABLE, WEBENGINE_INPROCESS_WEBGL_AVAILABLE, WVM_INPROCESS, WVM_EMBEDDED_EXTERNAL, WVM_EXTERNAL_WINDOW
from .gui.webviewcommon import WEBVIEWTYPE_NONE, WEBVIEWTYPE_WEBKIT, WEBVIEWTYPE_WEBENGINE
from .utils import logger, pluginDir, removeTemporaryOutputDir, settingsFilePath


class Qgis2threejs:

    PREFER_WEBKIT_SETTING = "/Qgis2threejs/preferWebKit"

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
        self.action.triggered.connect(self.openExporter)

        self.iface.addWebToolBarIcon(self.action)

        # web menu items
        self.actionGroup = QActionGroup(wnd)
        self.actionGroup.setObjectName(objName + "Group")

        self.actionWebEng = self.actionWebEngEE = self.actionWebEngEW = self.actionWebKit = None
        actions = []

        if Qgis.QGIS_VERSION_INT >= 33600:
            if WEBENGINE_INPROCESS_WEBGL_AVAILABLE:
                self.actionWebEng = QAction(icon, title + " (In Process WebEngine)", self.actionGroup)
                self.actionWebEng.setObjectName(objName + "WebEng")
                self.actionWebEng.triggered.connect(self.openExporterWebEng)
                actions.append(self.actionWebEng)

            self.actionWebEngEE = QAction(icon, title + " (Embedded External WebEngine)", self.actionGroup)
            self.actionWebEngEE.setObjectName(objName + "WebEngEE")
            self.actionWebEngEE.triggered.connect(self.openExporterEmbeddedExtenal)
            actions.append(self.actionWebEngEE)

            self.actionWebEngEW = QAction(icon, title + " (External Window)", self.actionGroup)
            self.actionWebEngEW.setObjectName(objName + "WebEngEW")
            self.actionWebEngEW.triggered.connect(self.openExporerExtenalWindow)
            actions.append(self.actionWebEngEW)

        if WEBKIT_AVAILABLE:
            self.actionWebKit = QAction(icon, title + " (WebKit)", self.actionGroup)
            self.actionWebKit.setObjectName(objName + "WebKit")
            self.actionWebKit.triggered.connect(self.openExporterWebKit)
            actions.append(self.actionWebKit)

        for action in actions:
            self.iface.addPluginToWebMenu(PLUGIN_NAME, action)

        self.menuActions = actions

        if False and Qgis.QGIS_VERSION_INT >= 33600 and WEBKIT_AVAILABLE:
            if WEBENGINE_AVAILABLE:
                self.actionWebEng.setCheckable(True)

            self.actionWebKit.setCheckable(True)

            if QSettings().value(self.PREFER_WEBKIT_SETTING, False) or not WEBENGINE_AVAILABLE:
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

        for action in self.menuActions:
            action.triggered.disconnect()
            self.iface.removePluginWebMenu(PLUGIN_NAME, action)

        # remove provider from processing registry
        QgsApplication.processingRegistry().removeProvider(self.pprovider)

        # temporary output directory
        removeTemporaryOutputDir()

    def openExporter(self, _=False, webViewType=None, webViewMode=None):
        """
        webViewType: WEBVIEWTYPE_NONE, WEBVIEWTYPE_WEBKIT, WEBVIEWTYPE_WEBENGINE or None. None means last used web view type.
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

    def openExporterEmbeddedExtenal(self):
        self.openExporter(webViewType=WEBVIEWTYPE_WEBENGINE, webViewMode=WVM_EMBEDDED_EXTERNAL)

    def openExporerExtenalWindow(self):
        self.openExporter(webViewType=WEBVIEWTYPE_WEBENGINE, webViewMode=WVM_EXTERNAL_WINDOW)

    def openExporterWebEng(self):
        if WEBENGINE_AVAILABLE:
            QSettings().remove(self.PREFER_WEBKIT_SETTING)
            self.openExporter(webViewType=WEBVIEWTYPE_WEBENGINE)
        else:
            self.openExporter(webViewType=WEBVIEWTYPE_NONE)

    def openExporterWebKit(self):
        self.openExporter(webViewType=WEBVIEWTYPE_WEBKIT)

        if WEBENGINE_AVAILABLE:
            QSettings().setValue(self.PREFER_WEBKIT_SETTING, True)

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
