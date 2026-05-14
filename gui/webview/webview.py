# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

from .const import WebViewType, WebViewMode
from .utils import logger

WEBENGINE_AVAILABLE = False
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView     # type: ignore
    WEBENGINE_AVAILABLE = True

except Exception as e:
    logger.warning(f"WebEngine widgets are unavailable: {e}")


def getWebViewClass(webViewType, webViewMode):
    if webViewType == WebViewType.WEBENGINE:
        if webViewMode == WebViewMode.INPROCESS:
            from .webengineview import Q3DWebEngineView
            return Q3DWebEngineView
        else:
            from .webviewproxy import Q3DWebViewProxy
            return Q3DWebViewProxy
    from .dummyview import Q3DDummyView
    return Q3DDummyView


def getWebPageClass(webViewType=WebViewType.WEBENGINE, webViewMode=WebViewMode.INPROCESS):
    if webViewType == WebViewType.WEBENGINE:
        if webViewMode == WebViewMode.INPROCESS:
            from .webengineview import Q3DWebEnginePage
            return Q3DWebEnginePage
        else:
            from .webviewproxy import Q3DWebPageProxy
            return Q3DWebPageProxy
    from .dummyview import Q3DDummyPage
    return Q3DDummyPage
