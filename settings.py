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

debug_mode = 1

class DefaultSettings:

  def __init__(self):
    self.baseSize = 100
    self.zExaggeration = 1.5
    self.zShift = 0

  def __getattr__(self, name):
    raise AttributeError

def_vals = DefaultSettings()
