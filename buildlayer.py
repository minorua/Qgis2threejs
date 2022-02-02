# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
        begin                : 2014-01-16
        copyright            : (C) 2014 Minoru Akagi
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
from qgis.core import QgsApplication


class LayerBuilder:

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
        return {"name": self.layer.name,
                "clickable": self.properties.get("checkBox_Clickable", True),
                "visible": self.properties.get("checkBox_Visible", True) or self.settings.isPreview}  # always visible in preview


def dummyProgress(percentage=None, msg=None):
    pass


def dummyLogMessage(msg, warning=False):
    pass
