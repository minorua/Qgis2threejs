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

plugin_version = "2.1"
debug_mode = 1
  # 0. no debug info
  # 1. JS console, qDebug
  # 2. JS console, qDebug, log file, "debug" element


class def_vals:

  template = "3DViewer.html"

  # world
  baseSize = 100
  zExaggeration = 1.0
  zShift = 0

  controls = "OrbitControls.js"    # last selected one has priority
