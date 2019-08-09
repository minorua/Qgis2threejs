# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
        begin                : 2013-12-21
        copyright            : (C) 2013 Minoru Akagi
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
# from PyQt5.QtCore import QSettings, QTranslator, qVersion
from PyQt5.QtWidgets import QAction
from PyQt5.QtGui import QIcon

from qgis.core import QgsApplication, QgsProject

from .procprovider import Qgis2threejsProvider
from .qgis2threejstools import logMessage, pluginDir, removeTemporaryOutputDir
from .q3dcontroller import Q3DController
from .q3dwindow import Q3DWindow


class Qgis2threejs:

    def __init__(self, iface):
        self.iface = iface
        self.pprovider = Qgis2threejsProvider()

        # initialize locale
        #locale = QSettings().value("locale/userLocale")[0:2]
        #localePath = os.path.join(self.plugin_dir, 'i18n', 'qgis2threejs_{0}.qm'.format(locale))

        #if os.path.exists(localePath):
        #  self.translator = QTranslator()
        #  self.translator.load(localePath)

        #  if qVersion() > '4.3.3':
        #    QCoreApplication.installTranslator(self.translator)

        self.currentProjectPath = None

        # exporter
        self.controller = None    # Q3DController

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
        if self.controller is None:
            self.controller = Q3DController(self.iface)

        if no_preview:
            self.controller.enabled = False

        if not self.controller.iface:
            logMessage("Opening Qgis2threejs Exporter...", False)

            proj_path = QgsProject.instance().fileName()
            if proj_path != self.currentProjectPath:
                self.controller.settings.loadSettingsFromFile()   # load export settings from settings file for current project
                self.currentProjectPath = proj_path

            self.liveExporter = Q3DWindow(self.iface.mainWindow(),
                                          self.iface,
                                          self.controller,
                                          preview=self.controller.enabled)
            self.liveExporter.show()
        else:
            logMessage("Qgis2threejs Exporter is already open.")
            self.liveExporter.activateWindow()

    def openExporterWithPreviewDisabled(self):
        self.openExporter(False, True)
