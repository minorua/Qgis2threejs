# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

from qgis.core import QgsApplication


class LayerBuilderBase:

    def __init__(self, settings, layer, imageManager=None, pathRoot=None, urlRoot=None, progress=None, log=None):
        self.settings = settings
        self.layer = layer
        self.properties = layer.properties

        self.imageManager = imageManager
        self.pathRoot = pathRoot
        self.urlRoot = urlRoot
        self.progress = progress or dummyProgress
        self.log = log or dummyLogMessage

        self._canceled = False

    def build(self):
        pass

    @property
    def canceled(self):
        if not self._canceled:
            QgsApplication.processEvents()
        return self._canceled

    @canceled.setter
    def canceled(self, value):
        self._canceled = value

    def cancel(self):
        self._canceled = True

    def _startBuildBlocks(self, cancelSignal):
        if cancelSignal:
            cancelSignal.connect(self.cancel)

    def _endBuildBlocks(self, cancelSignal):
        if cancelSignal:
            cancelSignal.disconnect(self.cancel)

    def layerProperties(self):
        return {
            "name": self.layer.name,
            "clickable": self.properties.get("checkBox_Clickable", True),
            "visible": self.properties.get("checkBox_Visible", True) or self.settings.isPreview    # always visible in preview
        }


def dummyProgress(percentage=None, msg=None):
    pass


def dummyLogMessage(msg, warning=False):
    pass
