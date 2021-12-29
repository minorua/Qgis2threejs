# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs Processing Provider
        begin                : 2018-11-06
        copyright            : (C) 2018 Minoru Akagi
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
from PyQt5.QtGui import QIcon
from qgis.core import QgsProcessingProvider

from processing.core.ProcessingConfig import ProcessingConfig, Setting

from .tools import pluginDir

QTO3_ACTIVE = "QGIS2THREEJS_ACTIVE"


class Qgis2threejsProvider(QgsProcessingProvider):

    def __init__(self):
        QgsProcessingProvider.__init__(self)
        self.algs = []

    def id(self):
        return "Qgis2threejs"

    def name(self):
        return "Qgis2threejs"

    def icon(self):
        return QIcon(pluginDir("Qgis2threejs.png"))

    def load(self):
        ProcessingConfig.settingIcons[self.name()] = self.icon()
        ProcessingConfig.addSetting(Setting(self.name(),
                                            QTO3_ACTIVE,
                                            self.tr("Activate"),
                                            False))
        ProcessingConfig.readSettings()
        self.refreshAlgorithms()
        return True

    def unload(self):
        ProcessingConfig.removeSetting(QTO3_ACTIVE)

    def isActive(self):
        return ProcessingConfig.getSetting(QTO3_ACTIVE)

    def setActive(self, active):
        ProcessingConfig.setSettingValue(QTO3_ACTIVE, active)

    def supportsNonFileBasedOutput(self):
        return False

    def loadAlgorithms(self):
        from .procalgorithm import ExportAlgorithm, ExportImageAlgorithm, ExportModelAlgorithm

        self.algs = [ExportAlgorithm(), ExportImageAlgorithm(), ExportModelAlgorithm()]
        for alg in self.algs:
            self.addAlgorithm(alg)
