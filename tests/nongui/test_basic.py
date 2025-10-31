# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-06

import importlib
import os
import sys
from qgis.testing import unittest

from Qgis2threejs.utils import logger, pluginDir


class TestBasic(unittest.TestCase):

    def test01_import_all_modules(self):
        """Test importing all modules in the plugin."""

        logger.info("Imported module list:")

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

                    if module not in sys.modules:
                        importlib.import_module(module)

                    logger.info(module)
                    imported += 1

        logger.info(f"Imported {imported} modules.")


if __name__ == "__main__":
    unittest.main()
