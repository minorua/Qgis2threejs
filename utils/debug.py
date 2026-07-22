# -*- coding: utf-8 -*-
# (C) 2024 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2024-10-28

import json
import sys
import weakref

from qgis.PyQt.QtCore import QDir, QObject

from .basic import pluginDir, temporaryOutputDir
from .logging import logger
from .gui import openDirectory

USE_OBJGRAPH = False

if USE_OBJGRAPH:
    import objgraph

num_destroyed = 0   # number of destroyed Qt object instances
num_finalized = 0   # number of Python objects that all references are gone


def objectsOfInterest(wnd):
    return [
        ("live exporter", wnd),
        ("controller", wnd.controller),
        ("builder", wnd.controller.builder),
        ("thread", wnd.controller.thread),
        ("web view", wnd.ui.webView),
        ("web page", wnd.ui.webView.page()),
        ("tree view", wnd.ui.treeView),
        ("animation panel", wnd.ui.animationPanel)
    ]


def setupDestructionLogging(wnd):
    global num_destroyed, num_finalized
    num_destroyed = num_finalized = 0

    for name, obj in objectsOfInterest(wnd):
        if obj:
            if isinstance(obj, QObject):
                obj.destroyed.connect(objectDestroyed)
            weakref.finalize(obj, objectFinalized, f"{name} finalized (Python).")


def objectDestroyed(obj):
    global num_destroyed
    num_destroyed += 1
    logger.debug(f"[{num_destroyed}] {obj.metaObject().className()} {obj.objectName()} destroyed (C++).")


def objectFinalized(msg):
    global num_finalized
    num_finalized += 1
    logger.debug(f"<{num_finalized}> {msg}")


def logReferenceCount(wnd):
    temp_dir = temporaryOutputDir()
    if USE_OBJGRAPH:
        QDir().mkpath(temp_dir)

    objs = objectsOfInterest(wnd)
    qobjs = []
    for name, obj in objs:
        if obj is None:
            logger.debug(f"{name} is None.")
            continue

        logger.debug(f"Number of ref. to {name} is {sys.getrefcount(obj)}.")

        if USE_OBJGRAPH:
            objgraph.show_backrefs(obj, max_depth=3, too_many=10, filename=temporaryOutputDir(f"ref_{name}.dot"))

        if isinstance(obj, QObject):
            qobjs.append(obj)

    logger.debug(f"Total objects: {len(objs)}, QObject: {len(qobjs)}")

    if USE_OBJGRAPH:
        openDirectory(temp_dir)


schema = None
def validateData(data):
    from jsonschema import validate, ValidationError

    global schema
    if not schema:
        with open(pluginDir("web/js/preview.schema.json"), "r") as f:
            schema = json.load(f)

    try:
        validate(data, schema)
        logger.debug("[VALIDATION] {} data is valid.".format(data.get("type")))

    except ValidationError as e:
        logger.warning(str(e))
        return e
