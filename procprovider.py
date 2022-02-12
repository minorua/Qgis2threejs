# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-06

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
