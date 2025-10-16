# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

from qgis.PyQt.QtCore import QSettings
from qgis.core import Qgis

from ..utils import logger

WEBVIEWTYPE_NONE = 0
WEBVIEWTYPE_WEBKIT = 1
WEBVIEWTYPE_WEBENGINE = 2

WEBENGINE_AVAILABLE = False
WEBKIT_AVAILABLE = False

if Qgis.QGIS_VERSION_INT >= 33600:
    try:
        from qgis.PyQt.QtWebEngineWidgets import QWebEngineView
        WEBENGINE_AVAILABLE = True

    except:
        pass

try:
    from qgis.PyQt.QtWebKitWidgets import QWebView
    WEBKIT_AVAILABLE = True

except:     # ModuleNotFoundError
    pass


if not (WEBENGINE_AVAILABLE or WEBKIT_AVAILABLE):
    logger.warning("Both webkit widgets and web engine widgets modules not found. The preview gets disabled.")


Q3DView = None
Q3DWebPage = None
currentWebViewType = None


def setCurrentWebView(webViewType):
    global Q3DView, Q3DWebPage, currentWebViewType

    if webViewType is currentWebViewType:
        return

    if webViewType == WEBVIEWTYPE_WEBKIT:
        from .q3dwebkitview import Q3DWebKitView, Q3DWebKitPage
        Q3DView = Q3DWebKitView
        Q3DWebPage = Q3DWebKitPage

    elif webViewType == WEBVIEWTYPE_WEBENGINE:
        from .q3dwebengineview import Q3DWebEngineView, Q3DWebEnginePage
        Q3DView = Q3DWebEngineView
        Q3DWebPage = Q3DWebEnginePage

    else:
        from .q3ddummyview import Q3DDummyView, Q3DDummyPage
        Q3DView = Q3DDummyView
        Q3DWebPage = Q3DDummyPage

    currentWebViewType = webViewType


if WEBKIT_AVAILABLE and QSettings().value("/Qgis2threejs/preferWebKit", False, type=bool):
    setCurrentWebView(WEBVIEWTYPE_WEBKIT)

elif WEBENGINE_AVAILABLE:
    setCurrentWebView(WEBVIEWTYPE_WEBENGINE)

elif WEBKIT_AVAILABLE:
    setCurrentWebView(WEBVIEWTYPE_WEBKIT)

else:
    setCurrentWebView(WEBVIEWTYPE_NONE)
