# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-03-02

# general
PLUGIN_NAME = "Qgis2threejs"
PLUGIN_VERSION = "2.8"
PLUGIN_VERSION_INT = 20800

# vector layer
FEATURES_PER_BLOCK = 50   # max number of features in a data block

# multi-threading
RUN_CNTLR_IN_BKGND = True    # If True, controller runs in a worker thread

# processing export
P_OPEN_DIRECTORY = True

# debug
DEBUG_MODE = 1
# 0. no debug info
# 1. log panel + JS console
# 2. log panel + JS console, log file, "debug" element


class DEF_SETS:

    # default export settings

    TEMPLATE = "3DViewer.html"

    # world
    Z_EXAGGERATION = 1.0
    Z_SHIFT = 0

    CONTROLS = "OrbitControls.js"    # last selected one has priority

    # dem
    SIDE_COLOR = "#ccbbaa"
    EDGE_COLOR = "#000000"
    WIREFRAME_COLOR = "#000000"
    TEXTURE_SIZE = 1024
    Z_BOTTOM = 0

    # vector
    LABEL_HEIGHT = 50
    LABEL_COLOR = "#000000"
    OTL_COLOR = "#ffffff"
    BG_COLOR = "#b0ffffff"
    CONN_COLOR = "#c0c0d0"

    # animation
    ANM_DURATION = 2000     # msec
