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
PLUGIN_VERSION = "2.3.1"

# DEBUG_MODE
#  0. no debug info
#  1. JS console, qDebug
#  2. JS console, qDebug, log file, "debug" element
DEBUG_MODE = 1

# multi-threading
RUN_CNTLR_IN_BKGND = True    # If True, controller runs in a worker thread

# vector layer
FEATURES_PER_BLOCK = 50   # max number of features in a data block

# default export settings


class DEF_SETS:

    TEMPLATE = "3DViewer.html"

    # world
    BASE_SIZE = 100
    Z_EXAGGERATION = 1.0
    Z_SHIFT = 0
    AUTO_Z_SHIFT = False

    CONTROLS = "OrbitControls.js"    # last selected one has priority

    # dem
    SIDE_COLOR = "0xccbbaa"

# processing export
P_OPEN_DIRECTORY = True
