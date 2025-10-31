# -*- coding: utf-8 -*-
# (C) 2025 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Classes and functions for logging

import os
import logging
from qgis.core import QgsMessageLog, Qgis

from ..conf import PLUGIN_NAME, DEBUG_MODE, TESTING


def pluginDir(*subdirs):
    p = os.path.dirname(os.path.dirname(__file__))
    if subdirs:
        return os.path.join(p, *subdirs)
    return p


class QgisLogHandler(logging.Handler):
    """A handler that logs messages to the QGIS log message panel."""
    def emit(self, record):
        msg = self.format(record)
        if record.levelno >= logging.ERROR:
            QgsMessageLog.logMessage(msg, tag=PLUGIN_NAME, level=Qgis.Critical, notifyUser=True)
        elif record.levelno >= logging.WARNING:
            QgsMessageLog.logMessage(msg, tag=PLUGIN_NAME, level=Qgis.Warning, notifyUser=True)
        else:
            QgsMessageLog.logMessage(msg, tag=PLUGIN_NAME, level=Qgis.Info, notifyUser=False)


class CallbackHandler(logging.Handler):

    ReplaceMap = {
        "warning": "warn",
        "critical": "error"
    }

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def emit(self, record):
        level = record.levelname.lower()
        level = self.ReplaceMap.get(level, level)
        self.callback(self.format(record), level)


def createLogger():
    logger = logging.getLogger(PLUGIN_NAME)
    logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

    if TESTING:
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        logger.addHandler(QgisLogHandler())

    if DEBUG_MODE == 2:
        formatter = logging.Formatter("[%(asctime)s - %(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        fileHandler = logging.FileHandler(pluginDir("qgis2threejs.log"), mode="w")
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)

    return logger

# the Logger
logger = createLogger()


def addLogCallback(callback):
    """Add a callback function that will be called when a message is logged.

    Args:
        callback: A function that takes message and level as arguments.
    """
    logger.addHandler(CallbackHandler(callback))


def removeLogCallback(callback):
    """Remove a previously added log callback function.

    Args:
        callback: The callback function to remove.
    """
    for handler in logger.handlers:
        if isinstance(handler, CallbackHandler) and handler.callback == callback:
            logger.removeHandler(handler)
            break
