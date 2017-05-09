# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2015-09-06

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
import qgis   # to set sip API version to 2
import sys
import os
import unittest
from PyQt4.QtNetwork import QNetworkDiskCache
from qgis.core import QgsApplication, QgsNetworkAccessManager

from .utilities import pluginPath, initOutputDir


def runTest():
  plugin_dir = pluginPath()
  plugins_dir = os.path.dirname(plugin_dir)

  # python path setting
  sys.path.append(plugins_dir)

  # initialize output directory
  initOutputDir()

  plugin_name = os.path.basename(plugin_dir)
  suite = unittest.TestLoader().discover(plugin_name + ".tests")
  unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
  gui_mode = True
  QGISAPP = QgsApplication(sys.argv, gui_mode)
  QGISAPP.initQgis()
  print("=" * 70)
  print(QGISAPP.showSettings())
  print("=" * 70)

  # set up network disk cache
  manager = QgsNetworkAccessManager.instance()
  cache = QNetworkDiskCache(manager)
  cache.setCacheDirectory(pluginPath(os.path.join("tests", "cache")))
  cache.setMaximumCacheSize(50 * 1024 * 1024)
  manager.setCache(cache)

  # run test!
  runTest()
