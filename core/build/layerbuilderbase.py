# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from ...utils import noop


class LayerBuilderBase:
    """Base class for layer builders that generate layer export data."""

    def __init__(self, layer, settings, imageManager=None, pathRoot=None, urlRoot=None, progress=None, log=None):
        """
        Args:
            layer: Layer object.
            settings: ExportSettings object.
            imageManager: Optional image manager used by material builders.
            pathRoot: Optional filesystem base path for exported assets.
            urlRoot: Optional URL base for exported assets.
            progress: Callable(current, total, msg) used to report progress.
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

    def build(self, build_blocks=False):
        """Generate the export data structure for this layer.

        Subclasses must implement this and return a dictionary
        that represents the layer's exportable data structure.
        """
        pass

    def blockCount(self):
        """Return the number of blocks in this layer.

        Used for progress reporting and may not be accurate.
        """
        return 1

    def blockBuilders(self):
        return []

    def layerProperties(self):
        """Return a dictionary with common layer properties used in export."""
        return {
            "name": self.layer.name,
            "clickable": self.properties.get("checkBox_Clickable", True),
            "visible": self.properties.get("checkBox_Visible", True) or self.settings.isPreview    # always visible in preview
        }
