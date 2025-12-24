# -*- coding: utf-8 -*-
# (C) 2024 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2024-10-28

import sys
import weakref

from .logging import logger

num_finalized = 0


def objectsOfInterest(wnd):
    objs = [
        ("live exporter", wnd),
        ("viewer interface", wnd.iface),
        ("controller", wnd.controller),
        ("builder", wnd.controller.builder),
        ("thread", wnd.controller.thread),
        ("web view", wnd.ui.webView),
        ("web page", wnd.ui.webView.page()),
        ("tree view", wnd.ui.treeView),
        ("animation panel", wnd.ui.animationPanel)
    ]
    return objs


def watchGarbageCollection(wnd):
    global num_finalized
    num_finalized = 0

    objs = objectsOfInterest(wnd)
    for i, (name, obj) in enumerate(objs):
        weakref.finalize(obj, objectFinalized, f"{len(objs)} {name} was garbage collected.")
        obj.destroyed.connect(objectDestroyed)


def objectFinalized(msg):
    global num_finalized
    num_finalized += 1
    logger.debug(f"{num_finalized}/{msg}")


def objectDestroyed(obj):
    logger.debug(f"{obj.metaObject().className()} {obj.objectName()} was destroyed.")


def logReferenceCount(wnd):
    for name, obj in objectsOfInterest(wnd):
        logger.debug(f"Number of ref. to {name} is {sys.getrefcount(obj)}.")
