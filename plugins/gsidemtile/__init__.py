# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GSIDEMTilePlugin - A Qgis2threejs plugin
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

class GSIDEMTilePlugin:

  @staticmethod
  def name():
    return "GSI DEM Tile Plugin"

  @staticmethod
  def type():
    return "demprovider"

  @staticmethod
  def providerName():
    return "GSI DEM Tile"

  @staticmethod
  def providerId():
    return "gsidemtile"

  @staticmethod
  def providerClass():
    from gsidemtileprovider import GSIDEMTileProvider
    return GSIDEMTileProvider

plugin_class = GSIDEMTilePlugin
