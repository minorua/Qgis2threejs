# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-03-02

# general
PLUGIN_NAME = "Qgis2threejs"
PLUGIN_VERSION = "2.6"
PLUGIN_VERSION_INT = int(float(PLUGIN_VERSION) * 100)

# 3d world coordinates
SHIFT_THRESHOLD = 10 ** 5   # When coordinate absolute values exceed this value, it is
                            # preferred to shift the coordinate to preserve precision

# vector layer
FEATURES_PER_BLOCK = 50   # max number of features in a data block

# animation
EASING = "Cubic"          # easing function name. one of Quadratic, Cubic, Quartic,
                          # Quintic, Sinusoidal, Exponential, Circular, Bounce

# multi-threading
RUN_CNTLR_IN_BKGND = True    # If True, controller runs in a worker thread

# processing export
P_OPEN_DIRECTORY = True

# debug
DEBUG_MODE = 1
# 0. no debug info
# 1. JS console, qDebug
# 2. JS console, qDebug, log file, "debug" element


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
