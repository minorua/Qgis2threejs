# -*- coding: utf-8 -*-
# (C) 2025 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
#
# Classes and functions for logging

import os
import logging

# This module may be used in an external process rather than within the QGIS process.
from PyQt6.QtCore import QDir, QObject, pyqtSignal

from ..conf import PLUGIN_NAME, DEBUG_MODE, TESTING


def pluginDir(*subdirs):
    p = os.path.dirname(os.path.dirname(__file__))
    if subdirs:
        return os.path.join(p, *subdirs)
    return p


def temporaryOutputDir(*subdirs):
    temp_dir = QDir.tempPath() + "/Qgis2threejs"
    if subdirs:
        return os.path.join(temp_dir, *subdirs)
    return temp_dir


QGIS_AVAILABLE = False
try:
    from qgis.core import QgsMessageLog, Qgis

    QGIS_AVAILABLE = True

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

except ImportError:
    pass


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


def getLogger(name=PLUGIN_NAME, stream=False, qgis_log=False, filepath="", list_handler=None):
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

    if QGIS_AVAILABLE and qgis_log:
        logger.addHandler(QgisLogHandler())

    if filepath:
        formatter = logging.Formatter("[%(asctime)s - %(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        fileHandler = logging.FileHandler(filepath, mode="w")
        fileHandler.setFormatter(formatter)
        logger.addHandler(fileHandler)

    if list_handler:
        logger.addHandler(list_handler)

    return logger


logger = web_logger = None

def configureLoggers(is_test=False, log_to_stream=False):
    """Configure the loggers. The loggers are created if not created yet."""
    global logger, web_logger

    list_handler = ListHandler() if is_test else None

    logger = getLogger(name=PLUGIN_NAME,
                       stream=log_to_stream,
                       qgis_log=not TESTING,
                       filepath=pluginDir("qgis2threejs.log") if DEBUG_MODE == 2 else "",
                       list_handler=list_handler)

    web_logger = getLogger(name=PLUGIN_NAME + "Web",
                           stream=log_to_stream,
                           filepath=pluginDir("qgis2threejs_web.log") if DEBUG_MODE == 2 else "",
                           list_handler=list_handler)

configureLoggers()


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


def clearListHandlerLogs(logger):
    """Clear logs stored in the ListHandler of the logger.

    Args:
        logger: The logger whose ListHandler logs will be cleared.
    """
    list_handler = getLogListHandler(logger)
    if list_handler:
        list_handler.clear()
