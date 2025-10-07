# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-05-22

import importlib
import sys

from qgis.PyQt.QtCore import QDir, QSettings
from .utils import logMessage, pluginDir


_pluginManager = None


def pluginManager(allPlugins=False):
    """allPlugins: for debug purpose"""
    global _pluginManager
    if _pluginManager is None:
        _pluginManager = PluginManager(allPlugins)
    return _pluginManager


class PluginManager:

    def __init__(self, allPlugins=False):
        self.allPlugins = allPlugins
        self.reloadPlugins()

    def reloadPlugins(self):
        self.modules = []
        self.plugins = []

        if self.allPlugins:
            plugin_dir = QDir(pluginDir("plugins"))
            plugins = plugin_dir.entryList(QDir.Filter.Dirs | QDir.Filter.NoSymLinks | QDir.Filter.NoDotAndDotDot)
        else:
            p = QSettings().value("/Qgis2threejs/plugins", "", type=str)
            plugins = p.split(",") if p else []

        for name in plugins:
            try:
                modname = "Qgis2threejs.plugins." + str(name)
                module = importlib.reload(sys.modules[modname]) if modname in sys.modules else importlib.import_module(modname)
                self.modules.append(module)
                self.plugins.append(getattr(module, "plugin_class"))
            except ImportError:
                logMessage("Failed to load plugin: " + str(name), error=True)

    def demProviderPlugins(self):
        plugins = []
        for plugin in self.plugins:
            if plugin.type() == "demprovider":
                plugins.append(plugin)
        return plugins

    def findDEMProvider(self, id):
        for plugin in self.plugins:
            if plugin.type() == "demprovider" and plugin.providerId() == id:
                return plugin.providerClass()
        return None
