# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2015-09-06

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
import sys
import os
import unittest
from PyQt5.Qt import Qt
from PyQt5.QtNetwork import QNetworkDiskCache

import qgis
from qgis.core import QgsApplication, QgsNetworkAccessManager
from qgis.testing import start_app

plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def runTest():
  # python path setting
  plugins_dir = os.path.dirname(plugin_dir)
  sys.path.append(plugins_dir)

  # initialize output directory
  from utilities import initOutputDir
  initOutputDir()

  plugin_name = os.path.basename(plugin_dir)
  suite = unittest.TestLoader().discover(plugin_name + ".tests")
  unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
  QgsApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
  QGISAPP = start_app()

  # set up network disk cache
  manager = QgsNetworkAccessManager.instance()
  cache = QNetworkDiskCache(manager)
  cache.setCacheDirectory(os.path.join(plugin_dir, "tests", "cache"))
  cache.setMaximumCacheSize(50 * 1024 * 1024)
  manager.setCache(cache)

  # run test!
  runTest()
