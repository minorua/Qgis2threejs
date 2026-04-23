# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

from qgis.PyQt.QtCore import QSettings
from qgis.core import Qgis

from ..utils import logger

# Web View Type
WEBVIEWTYPE_NONE = 0
WEBVIEWTYPE_WEBKIT = 1      # TODO: remove
WEBVIEWTYPE_WEBENGINE = 2

# Web View Mode
WVM_INPROCESS = 0
WVM_EMBEDDED_EXTERNAL = 1
WVM_EXTERNAL_WINDOW = 2

WEBENGINE_AVAILABLE = False
WEBKIT_AVAILABLE = False

if Qgis.QGIS_VERSION_INT >= 33600:
    try:
        from qgis.PyQt.QtWebEngineWidgets import QWebEngineView     # type: ignore
        WEBENGINE_AVAILABLE = True

    except Exception as e:
        logger.warning(f"WebEngine widgets are unavailable: {e}")

try:
    from qgis.PyQt.QtWebKitWidgets import QWebView      # type: ignore
    WEBKIT_AVAILABLE = True

except:     # ModuleNotFoundError
    pass

if not (WEBENGINE_AVAILABLE or WEBKIT_AVAILABLE):
    logger.warning("Neither WebKit nor WebEngine modules are available.")


defaultWebViewType = None
Q3DView = None
Q3DWebPage = None


def getWebViewClass(webViewType=None, webViewMode=None):
    if webViewType is None:
        if defaultWebViewType is None:
            webViewType = WEBVIEWTYPE_WEBENGINE
        else:
            webViewType = defaultWebViewType

    if webViewMode is None:
        webViewMode = WVM_INPROCESS

    if webViewType == WEBVIEWTYPE_WEBKIT:
        from .webkitview import Q3DWebKitView
        return Q3DWebKitView

    if webViewType == WEBVIEWTYPE_WEBENGINE:
        from .webengineview import Q3DWebEngineView
        return Q3DWebEngineView

    from .fallbackview import Q3DFallbackView
    return Q3DFallbackView


def getWebPageClass(webViewType=WEBVIEWTYPE_WEBENGINE, webViewMode=WVM_INPROCESS):
    if webViewType == WEBVIEWTYPE_WEBKIT:
        from .webkitview import Q3DWebKitPage
        return Q3DWebKitPage

    if webViewType == WEBVIEWTYPE_WEBENGINE:
        from .webengineview import Q3DWebEnginePage
        return Q3DWebEnginePage

    from .fallbackview import Q3DFallbackPage
    return Q3DFallbackPage


def setDefaultWebView(webViewType):
    global Q3DView, Q3DWebPage, defaultWebViewType

    if webViewType is defaultWebViewType:
        return

    if webViewType == WEBVIEWTYPE_WEBKIT:
        from .webkitview import Q3DWebKitView, Q3DWebKitPage
        Q3DView = Q3DWebKitView
        Q3DWebPage = Q3DWebKitPage

    elif webViewType == WEBVIEWTYPE_WEBENGINE:
        from .webengineview import Q3DWebEngineView, Q3DWebEnginePage
        Q3DView = Q3DWebEngineView
        Q3DWebPage = Q3DWebEnginePage

    else:
        from .fallbackview import Q3DFallbackView, Q3DFallbackPage
        Q3DView = Q3DFallbackView
        Q3DWebPage = Q3DFallbackPage

    defaultWebViewType = webViewType


if WEBKIT_AVAILABLE and QSettings().value("/Qgis2threejs/preferWebKit", False, type=bool):
    setDefaultWebView(WEBVIEWTYPE_WEBKIT)

elif WEBENGINE_AVAILABLE:
    setDefaultWebView(WEBVIEWTYPE_WEBENGINE)

elif WEBKIT_AVAILABLE:
    setDefaultWebView(WEBVIEWTYPE_WEBKIT)

else:
    setDefaultWebView(WEBVIEWTYPE_NONE)
