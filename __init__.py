# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2013-12-21

def classFactory(iface):
    # load Qgis2threejs class from file Qgis2threejs
    from .qgis2threejs import Qgis2threejs
    return Qgis2threejs(iface)
