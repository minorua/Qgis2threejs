# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2013-12-21

import os

from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtWidgets import QAction, QActionGroup, QMessageBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import Qgis, QgsApplication, QgsProject

from .conf import DEBUG_MODE, PLUGIN_NAME
from .core.exportsettings import ExportSettings
from .core.processing.procprovider import Qgis2threejsProvider
from .gui.q3dwindow import Q3DWindow
from .gui.q3dview import WEBENGINE_AVAILABLE, WEBKIT_AVAILABLE, WEBVIEWTYPE_NONE, WEBVIEWTYPE_WEBKIT, WEBVIEWTYPE_WEBENGINE, currentWebViewType
from .utils import logMessage, pluginDir, removeTemporaryOutputDir, settingsFilePath


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

        if Qgis.QGIS_VERSION_INT >= 33600:
            self.actionWebEng = QAction(icon, title + " (WebEngine)", self.actionGroup)
            self.actionWebEng.setObjectName(objName + "WebEng")
            self.actionWebEng.triggered.connect(self.openExporterWebEng)

            self.iface.addPluginToWebMenu(PLUGIN_NAME, self.actionWebEng)

        if WEBKIT_AVAILABLE:
            self.actionWebKit = QAction(icon, title + " (WebKit)", self.actionGroup)
            self.actionWebKit.setObjectName(objName + "WebKit")
            self.actionWebKit.triggered.connect(self.openExporterWebKit)

            self.iface.addPluginToWebMenu(PLUGIN_NAME, self.actionWebKit)

        if Qgis.QGIS_VERSION_INT >= 33600 and WEBKIT_AVAILABLE:
            if WEBENGINE_AVAILABLE:
                self.actionWebEng.setCheckable(True)

            self.actionWebKit.setCheckable(True)

            if QSettings().value("/Qgis2threejs/preferWebKit", False) or not WEBENGINE_AVAILABLE:
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

        if Qgis.QGIS_VERSION_INT >= 33600:
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
            logMessage("Qgis2threejs Exporter is already open.")
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

        self.liveExporter = Q3DWindow(self.iface,
                                      self.exportSettings,
                                      webViewType=webViewType,
                                      previewEnabled=self.previewEnabled)
        self.liveExporter.show()
        self.liveExporter.destroyed.connect(self.exporterDestroyed)

        self.currentProjectPath = proj_path

    def openExporterWebEng(self):
        if WEBENGINE_AVAILABLE:
            self.openExporter(webViewType=WEBVIEWTYPE_WEBENGINE)

            QSettings().remove("/Qgis2threejs/preferWebKit")
            return

        url = "https://github.com/minorua/Qgis2threejs/wiki/How-to-use-Qt-WebEngine-view-with-Qgis2threejs"

        msgBox = QMessageBox()
        msgBox.setTextFormat(Qt.TextFormat.RichText)
        msgBox.setText("PyQt-WebEngine is not installed. See <a href='{}'>wiki page</a> for details.".format(url))
        msgBox.setWindowTitle("Qgis2threejs")

        msgBox.exec()

    def openExporterWebKit(self):
        self.openExporter(webViewType=WEBVIEWTYPE_WEBKIT)

        if WEBENGINE_AVAILABLE:
            QSettings().setValue("/Qgis2threejs/preferWebKit", True)

    def exporterDestroyed(self, obj):
        if currentWebViewType != WEBVIEWTYPE_NONE:
            self.previewEnabled = self.liveExporter.controller.enabled      # remember preview state

        if DEBUG_MODE:
            from .utils.debug_utils import logReferenceCount
            logReferenceCount(self.liveExporter)

        self.liveExporter = None

    def allLayersRemoved(self):
        self.currentProjectPath = ""
        self.exportSettings = None
