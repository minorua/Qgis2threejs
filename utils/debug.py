# -*- coding: utf-8 -*-
# (C) 2024 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2024-10-28

import sys
import weakref

from .logging import python_logger as logger


def objectsOfInterest(wnd):
    objs = [("live exporter", wnd),
            ("viewer interface", wnd.iface),
            ("controller", wnd.controller),
            ("web view", wnd.ui.webView),
            ("web page", wnd.ui.webView.page()),
            ("tree view", wnd.ui.treeView),
            ("animation panel", wnd.ui.animationPanel),
            ("animation tree", wnd.ui.animationPanel.ui.treeWidgetAnimation)]
    return objs


def watchGarbageCollection(wnd):
    objs = objectsOfInterest(wnd)
    for i, (name, obj) in enumerate(objs):
        weakref.finalize(obj, logger.debug, "({}/{}) {} was garbage collected.".format(i + 1, len(objs), name))
        obj.destroyed.connect(objectDestroyed)


def objectDestroyed(obj):
    logger.debug("{} {} was destroyed.".format(obj.metaObject().className(), obj.objectName()))


def logReferenceCount(wnd):
    for name, obj in objectsOfInterest(wnd):
        logger.debug("Number of ref. to {} is {}.".format(name, sys.getrefcount(obj)))
