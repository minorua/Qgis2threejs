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

# threading
RUN_BLDR_IN_BKGND = True    # If True, builders run in a worker thread

# processing export
P_OPEN_DIRECTORY = True

# debugging and testing
DEBUG_MODE = 1

# DEBUG_MODE values:
#  0: No debug output
#  1: Output debug information to log panel and/or JS console
#  2: Same as 1, plus write debug information to log files

TEMP_DEBUG_MODE = DEBUG_MODE    # temporary code for debugging
TESTING = False

# help
HELP_URL_BASE = "https://minorua.github.io/Qgis2threejs/help/"


# default export settings
class DEF_SETS:

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
