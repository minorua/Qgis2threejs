# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import QSize

from ....conf import DEF_SETS


class DEMPropertyReader:

    @staticmethod
    def opacity(mtlProperties):
        return mtlProperties.get("spinBox_Opacity", 100) / 100

    @staticmethod
    def textureSize(mtlProperties, extent, settings):
        try:
            w = int(mtlProperties.get("comboBox_TextureSize", DEF_SETS.TEXTURE_SIZE))
        except ValueError:
            w = DEF_SETS.TEXTURE_SIZE

        return QSize(w, round(w * extent.height() / extent.width()))
