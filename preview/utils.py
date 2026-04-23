# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
import os
import logging as logger

from PyQt6.QtCore import qDebug


def _patched_log(msg, *args, **kwargs):
    qDebug(str(msg).encode("utf-8"))


logger.debug = _patched_log
logger.info = _patched_log
logger.warning = _patched_log
logger.error = _patched_log


def pluginDir(*subdirs):
    p = os.path.dirname(os.path.dirname(__file__))
    if subdirs:
        return os.path.join(p, *subdirs)
    return p
