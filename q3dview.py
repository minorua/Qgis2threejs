# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

from qgis.core import Qgis
from .utils import logMessage

WEBVIEWTYPE_NONE = 0
WEBVIEWTYPE_WEBKIT = 1
WEBVIEWTYPE_WEBENGINE = 2

WEBENGINE_AVAILABLE = False
WEBKIT_AVAILABLE = False

if Qgis.QGIS_VERSION_INT >= 33800:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        WEBENGINE_AVAILABLE = True

    except:
        pass

try:
    from PyQt5.QtWebKitWidgets import QWebView
    WEBKIT_AVAILABLE = True

except:     # ModuleNotFoundError
    pass


if not (WEBENGINE_AVAILABLE or WEBKIT_AVAILABLE):
    logMessage("Both webkit widgets and web engine widgets modules not found. The preview gets disabled.")


Q3DView = None
Q3DWebPage = None
currentWebViewType = None
