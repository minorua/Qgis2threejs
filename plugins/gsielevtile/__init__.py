# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-05-22

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
