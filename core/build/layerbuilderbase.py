# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from threading import Lock

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import pyqtSlot

from ...utils import noop


class LayerBuilderBase:
    """Base class for layer builders that generate layer export data."""

    def __init__(self, settings, layer, imageManager=None, pathRoot=None, urlRoot=None, progress=None, log=None, isInUiThread=True):
        """
        Args:
            settings: ExportSettings object.
            layer: Layer object.
            imageManager: Optional image manager used by material builders.
            pathRoot: Optional filesystem base path for exported assets.
            urlRoot: Optional URL base for exported assets.
            progress: Callable(percentage, msg) used to report progress.
            log: Callable(message, warning) for logging messages.
            isInUiThread: Let me know whether three.js builder and this layer builder run in the UI thread or not.
        """
        self.settings = settings
        self.layer = layer
        self.properties = layer.properties

        self.imageManager = imageManager
        self.pathRoot = pathRoot
        self.urlRoot = urlRoot
        self.progress = progress or noop
        self.log = log or noop

        self._aborted = False
        self._isInUiThread = isInUiThread
        self._lock = Lock()

    def build(self, build_blocks=False, abortSignal=None):
        """Generate the export data structure for this layer.

        Subclasses must implement this and return a dictionary
        that represents the layer's exportable data structure
        (or `None` if the build was aborted).
        """
        pass

    @property
    def aborted(self):
        """Property returning whether a cancel has been requested."""
        if self._isInUiThread:
            QgsApplication.processEvents()
            return self._aborted

        with self._lock:
            return self._aborted

    @aborted.setter
    def aborted(self, value):
        if self._isInUiThread:
            self._aborted = value
            return

        with self._lock:
            self._aborted = value

    @pyqtSlot()
    def abort(self):
        """Interrupts any ongoing work by setting the cancellation flag."""
        self.aborted = True

    def _startBuildBlocks(self, abortSignal):
        """Connect a Qt cancellation signal to this builder."""
        if abortSignal:
            abortSignal.connect(self.abort)

    def _endBuildBlocks(self, abortSignal):
        """Disconnect a previously-connected cancellation signal."""
        if abortSignal:
            abortSignal.disconnect(self.abort)

    def layerProperties(self):
        """Return a dictionary with common layer properties used in export."""
        return {
            "name": self.layer.name,
            "clickable": self.properties.get("checkBox_Clickable", True),
            "visible": self.properties.get("checkBox_Visible", True) or self.settings.isPreview    # always visible in preview
        }
