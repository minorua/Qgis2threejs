# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GSIElevTilePlugin - A Qgis2threejs plugin
                              -------------------
        begin                : 2015-05-22
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


class GSIElevTilePlugin:

  @staticmethod
  def name():
    return "GSI Elevation Tile Plugin"

  @staticmethod
  def type():
    return "demprovider"

  @staticmethod
  def providerName():
    return "GSI Elevation Tile"

  @staticmethod
  def providerId():
    return "gsielevtile"

  @staticmethod
  def providerClass():
    from .gsielevtileprovider import GSIElevTileProvider
    return GSIElevTileProvider

plugin_class = GSIElevTilePlugin
