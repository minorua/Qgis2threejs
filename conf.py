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
DEBUG_MODE = 1
  # 0. no debug info
  # 1. JS console, qDebug
  # 2. JS console, qDebug, log file, "debug" element

# vector layer
BLOCK_FEATURES = 50   # max number of features in a block of vector layer features

# default export settings
class DEF_SETS:

  TEMPLATE = "3DViewer.html"

  # world
  BASE_SIZE = 100
  Z_EXAGGERATION = 1.0
  Z_SHIFT = 0
  AUTO_Z_SHIFT = False

  CONTROLS = "OrbitControls.js"    # last selected one has priority

# processing export
P_OPEN_DIRECTORY = True
