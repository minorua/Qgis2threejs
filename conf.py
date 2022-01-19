# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DefaultSettings
                             -------------------
        begin                : 2015-03-02
        copyright            : (C) 2015 Minoru Akagi
        email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

# general
PLUGIN_VERSION = "2.6"
PLUGIN_VERSION_INT = int(float(PLUGIN_VERSION) * 100)

# 3d world coordinates
SHIFT_THRESHOLD = 10 ** 5   # When coordinate absolute values exceed this value, shifting
                            # the coordinate is preferred to preserve precision

# vector layer
FEATURES_PER_BLOCK = 50   # max number of features in a data block

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
    AUTO_Z_SHIFT = False

    CONTROLS = "OrbitControls.js"    # last selected one has priority

    # dem
    SIDE_COLOR = "0xccbbaa"
    EDGE_COLOR = "0x000000"
    WIREFRAME_COLOR = "0x000000"
    TEXTURE_SIZE = 1024
    Z_BOTTOM = 0

    # animation
    ANM_DURATION = 2000     # msec
