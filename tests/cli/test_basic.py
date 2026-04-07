# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-06

import importlib
import os
import sys

try:
    from qgis.testing import unittest
except ImportError:
    import unittest

try:
    from .utils import logger
    logger.info("Using the logger configured for Qgis2threejs testing.")
except ImportError:
    import logging
    logger = logging.getLogger("Qgis2threejs")
    logger.setLevel(logging.DEBUG)
    logger.info("Using a logger not configured for Qgis2threejs testing.")


class TestBasic(unittest.TestCase):

    def test01_start_qgis(self):
        """Test starting QGIS application."""

        logger.info(f"Python Executable: {sys.executable}")
        logger.info(f"Python Version: {sys.version}")
        logger.info(f"Python Path: {sys.path}")

        from qgis.PyQt.QtCore import PYQT_VERSION_STR, QT_VERSION_STR
        from qgis.core import Qgis

        logger.info(f"PYQT_VERSION: {PYQT_VERSION_STR}")
        logger.info(f"QT_VERSION: {QT_VERSION_STR}")
        logger.info(f"QGIS_VERSION: {Qgis.QGIS_VERSION}")

        from .utils import start_app, stop_app

        app = start_app()
        self.assertIsNotNone(app, "Failed to start QGIS application.")
        stop_app()

    def test02_import_all_modules(self):
        """Test importing all modules in the plugin."""

        from ...utils import pluginDir

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
