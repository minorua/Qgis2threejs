# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-06

import importlib
import os
import sys
from qgis.testing import unittest

from Qgis2threejs.tests.utilities import pluginDir


class TestBasic(unittest.TestCase):

    def test01_import(self):
        """module import test"""
        plugin_dir = pluginDir()
        imported = 0
        for package_dir in ["", "/plugins/gsielevtile"]:
            for filename in os.listdir(plugin_dir + package_dir):
                if filename[-3:] != ".py" or filename == "__init__.py":
                    continue

                module = "Qgis2threejs"
                if package_dir:
                    module += "." + package_dir[1:].replace("/", ".")
                module += "." + filename[:-3]

                if module not in sys.modules:
                    # print "load: " + module
                    importlib.import_module(module)
                else:
                    # print "reload: " + module
                    # reload(sys.modules[module])
                    pass
                imported += 1

        print("{0} modules imported".format(imported))


if __name__ == "__main__":
    unittest.main()
