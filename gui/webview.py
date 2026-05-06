# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

from qgis.PyQt.QtCore import QSettings
from qgis.core import Qgis

from .webviewcommon import WEBVIEWTYPE_NONE, WEBVIEWTYPE_WEBENGINE
from ..utils import logger

# Web View Mode
WVM_INPROCESS = 0
WVM_EMBEDDED_EXTERNAL = 1
WVM_EXTERNAL_WINDOW = 2

WEBENGINE_AVAILABLE = False
WEBENGINE_INPROCESS_WEBGL_AVAILABLE = True


if Qgis.QGIS_VERSION_INT >= 33600:
    try:
        from qgis.PyQt.QtWebEngineWidgets import QWebEngineView     # type: ignore
        WEBENGINE_AVAILABLE = True

    except Exception as e:
        logger.warning(f"WebEngine widgets are unavailable: {e}")


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

    if webViewType == WEBVIEWTYPE_WEBENGINE:
        if webViewMode == WVM_INPROCESS:
            from .webengineview import Q3DWebEngineView
            return Q3DWebEngineView

        from .webviewproxy import Q3DWebViewProxy
        return Q3DWebViewProxy

    from .fallbackview import Q3DFallbackView
    return Q3DFallbackView


def getWebPageClass(webViewType=WEBVIEWTYPE_WEBENGINE, webViewMode=WVM_INPROCESS):
    if webViewType == WEBVIEWTYPE_WEBENGINE:
        if webViewMode == WVM_INPROCESS:
            from .webengineview import Q3DWebEnginePage
            return Q3DWebEnginePage

        from .webviewproxy import Q3DWebPageProxy
        return Q3DWebPageProxy

    from .fallbackview import Q3DFallbackPage
    return Q3DFallbackPage


def setDefaultWebView(webViewType, webViewMode=WVM_INPROCESS):
    global Q3DView, Q3DWebPage, defaultWebViewType

    if webViewType is defaultWebViewType:
        return

    elif webViewType == WEBVIEWTYPE_WEBENGINE:
        if webViewMode == WVM_INPROCESS:
            from .webengineview import Q3DWebEngineView, Q3DWebEnginePage
            Q3DView = Q3DWebEngineView
            Q3DWebPage = Q3DWebEnginePage
        else:
            from.webviewproxy import Q3DWebViewProxy, Q3DWebPageProxy
            Q3DView = Q3DWebViewProxy
            Q3DWebPage = Q3DWebPageProxy

    else:
        from .fallbackview import Q3DFallbackView, Q3DFallbackPage
        Q3DView = Q3DFallbackView
        Q3DWebPage = Q3DFallbackPage

    defaultWebViewType = webViewType


if WEBENGINE_AVAILABLE:
    setDefaultWebView(WEBVIEWTYPE_WEBENGINE)

else:
    setDefaultWebView(WEBVIEWTYPE_NONE)
