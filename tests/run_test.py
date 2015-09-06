# -*- coding: utf-8 -*-
"""
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
__author__ = "Minoru Akagi"
__date__ = "2015-09-06"


import sys
if __name__ == "__main__":
  import sip
  try:
    for api in ["QDate", "QDateTime", "QString", "QTextStream", "QTime", "QUrl", "QVariant"]:
      sip.setapi(api, 2)
  except Exception as e:
    print "Failed to set sip API version"
    print e.message
    sys.exit(1)

import imp
import os
import unittest


def runTest():
  tests_dir = os.path.dirname(os.path.abspath(__file__).decode(sys.getfilesystemencoding()))
  plugin_dir = os.path.dirname(tests_dir)
  plugins_dir = os.path.dirname(plugin_dir)

  # python path setting
  sys.path.append(plugins_dir)
  #print str(sys.path)

  plugin_name = os.path.basename(plugin_dir)
  suite = unittest.TestLoader().discover(plugin_name + ".tests")
  unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
  from qgis.core import QgsApplication

  gui_mode = True
  QGISAPP = QgsApplication(sys.argv, gui_mode)
  QGISAPP.initQgis()
  print "=" * 70
  print QGISAPP.showSettings()
  print "=" * 70

  # run test!
  runTest()
