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


class ListHandler(logging.Handler):
    """A handler that stores log records in a list."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)

    def clear(self):
        self.records.clear()

    def get_records(self):
        return self.records

    def get_messages(self):
        """Return a list of formatted messages."""
        return [self.format(record) for record in self.records]


def getLogger(name=PLUGIN_NAME, stream=False, qgis_log=False, filepath="", list_handler=False):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
    logger.propagate = False

    for handler in logger.handlers[:]:      # copy the list
        logger.removeHandler(handler)
        handler.close()

    if stream:
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    if qgis_log:
        logger.addHandler(QgisLogHandler())

    if filepath:
        formatter = logging.Formatter("[%(asctime)s - %(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        fileHandler = logging.FileHandler(filepath, mode="w")
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)

    if list_handler:
        logger.addHandler(ListHandler())

    return logger


# the Loggers
python_logger = getLogger(name=PLUGIN_NAME,
                          stream=TESTING,
                          qgis_log=not TESTING,
                          filepath=pluginDir("qgis2threejs.log") if DEBUG_MODE == 2 else "")

web_logger = getLogger(name=PLUGIN_NAME + "Web",
                       filepath=pluginDir("qgis2threejs_web.log") if DEBUG_MODE == 2 else "")


def addLogCallback(logger, callback):
    """Add a callback function that will be called when a message is logged.

    Args:
        callback: A function that takes message and level as arguments.
    """
    logger.addHandler(CallbackHandler(callback))


def removeLogCallback(logger, callback):
    """Remove a previously added log callback function.

    Args:
        callback: The callback function to remove.
    """
    for handler in logger.handlers:
        if isinstance(handler, CallbackHandler) and handler.callback == callback:
            logger.removeHandler(handler)
            break


def addLogListHandler(logger):
    """Add a ListHandler to the logger.

    Args:
        logger: The logger to which the ListHandler will be added.
    """
    logger.addHandler(ListHandler())


def getLogListHandler(logger):
    """Get the ListHandler from the logger.

    Args:
        logger: The logger from which the ListHandler will be retrieved.

    Returns:
        The ListHandler instance if found, None otherwise.
    """
    for handler in logger.handlers:
        if isinstance(handler, ListHandler):
            return handler
    return None


def removeLogListHandler(logger):
    """Remove a ListHandler from the logger.

    Args:
        logger: The logger from which a ListHandler will be removed.
    """
    for handler in logger.handlers:
        if isinstance(handler, ListHandler):
            logger.removeHandler(handler)
            break
