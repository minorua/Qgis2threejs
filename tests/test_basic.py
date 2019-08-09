# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2015-09-06

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
import importlib
import os
import sys
from qgis.testing import start_app, unittest

from utilities import pluginPath

QGISAPP = start_app()


class TestBasic(unittest.TestCase):

    def test01_import(self):
        """module import test"""
        plugin_dir = pluginPath()
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
