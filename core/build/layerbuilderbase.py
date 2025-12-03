# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.core import QgsApplication

from ...utils import noop


class LayerBuilderBase:
    """Base class for layer builders that generate layer export data."""

    def __init__(self, settings, layer, imageManager=None, pathRoot=None, urlRoot=None, progress=None, log=None):
        """
        Args:
            settings: ExportSettings object.
            layer: Layer object.
            imageManager: Optional image manager used by material builders.
            pathRoot: Optional filesystem base path for exported assets.
            urlRoot: Optional URL base for exported assets.
            progress: Callable(percentage, msg) used to report progress.
            log: Callable(message, warning) for logging messages.
        """
        self.settings = settings
        self.layer = layer
        self.properties = layer.properties

        self.imageManager = imageManager
        self.pathRoot = pathRoot
        self.urlRoot = urlRoot
        self.progress = progress or noop
        self.log = log or noop

        # internal cancellation flag
        self._canceled = False

    def build(self):
        """Generate the export data structure for this layer.

        Subclasses must implement this and return a dictionary
        that represents the layer's exportable data structure
        (or `None` if the build was canceled).
        """
        pass

    @property
    def canceled(self):
        """Property returning whether a cancel has been requested."""
        if not self._canceled:
            QgsApplication.processEvents()
        return self._canceled

    @canceled.setter
    def canceled(self, value):
        self._canceled = value

    def cancel(self):
        """Interrupts any ongoing work by setting the cancellation flag."""
        self._canceled = True

    def _startBuildBlocks(self, cancelSignal):
        """Connect a Qt cancellation signal to this builder."""
        if cancelSignal:
            cancelSignal.connect(self.cancel)

    def _endBuildBlocks(self, cancelSignal):
        """Disconnect a previously-connected cancellation signal."""
        if cancelSignal:
            cancelSignal.disconnect(self.cancel)

    def layerProperties(self):
        """Return a dictionary with common layer properties used in export."""
        return {
            "name": self.layer.name,
            "clickable": self.properties.get("checkBox_Clickable", True),
            "visible": self.properties.get("checkBox_Visible", True) or self.settings.isPreview    # always visible in preview
        }
