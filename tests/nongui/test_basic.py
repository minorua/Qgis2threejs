# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-06

import importlib
import os
import sys
from qgis.testing import unittest
from logging import getLogger

from Qgis2threejs.tests.utilities import logger, pluginDir

#from Qgis2threejs import utils

#import logging
#logging.basicConfig(level=logging.DEBUG)

#from logging import getLogger, Formatter, DEBUG
#logger = getLogger("Qgis2threejs")
#format = Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# logger.setFormatter(format)
#logger.setLevel(DEBUG)
#utils.logger = logger


class TestBasic(unittest.TestCase):

    def test01_import_all_modules(self):
        """Test importing all modules in the plugin."""
        print("Hello!")

        with open("D:/test.log", "a") as f:
            f.write("Test importing all modules in the plugin...\n")
            f.write(f"pluginDir: {pluginDir()}\n")
            f.write(f"sys.path: {sys.path}\n")
            f.write(f"QGIS_PREFIX_PATH: {os.environ.get('QGIS_PREFIX_PATH', '')}\n")
            f.write(f"PYTHONPATH: {os.environ.get('PYTHONPATH', '')}\n")
            f.write(f"PATH: {os.environ.get('PATH', '')}\n")
            f.write(f"QT_PLUGIN_PATH: {os.environ.get('QT_PLUGIN_PATH', '')}\n")

            # どこで設定されているの?

        total = 0
        imported = 0
        plugin_dir = pluginDir()
        for sub_dir in ["core", "gui", "lib", "plugins", "utils"]:
            for root, _, files in os.walk(os.path.join(plugin_dir, sub_dir)):
                for filename in files:
                    if not filename.endswith(".py") or filename == "__init__.py":
                        continue
                    relpath = os.path.relpath(os.path.join(root, filename), plugin_dir)
                    module_name = relpath[:-3].replace(os.path.sep, ".")
                    module = "Qgis2threejs." + module_name

                    logger.warning(module)

                    if module not in sys.modules:
                        importlib.import_module(module)
                        logger.info(f"{module} imported.")
                    imported += 1
                    total += 1

        logger.warning(f"{imported} modules imported.")

        # self.assertEqual(imported, total, f"Imported {imported} modules (expected {total}).")
        print(f"QGIS_PREFIX_PATH: {os.environ['QGIS_PREFIX_PATH']}")


if __name__ == "__main__":
    unittest.main()
