# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03


from .conf import PREFER_WEBKIT
from .utils import logMessage

USE_WEBKIT = False
USE_WEBENGINE = False

if PREFER_WEBKIT:
    try:
        from PyQt5.QtWebKitWidgets import QWebView
        USE_WEBKIT = True

    except ModuleNotFoundError:
        pass

    if not USE_WEBKIT:
        try:
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            USE_WEBENGINE = True

        except ModuleNotFoundError:
            pass

else:
    try:
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        USE_WEBENGINE = True

    except ModuleNotFoundError:
        pass

    if not USE_WEBENGINE:
        try:
            from PyQt5.QtWebKitWidgets import QWebView
            USE_WEBKIT = True

        except ModuleNotFoundError:
            pass

if USE_WEBKIT:
    from .q3dwebkitview import Q3DWebKitView as Q3DView, Q3DWebKitPage as Q3DWebPage

elif USE_WEBENGINE:
    from .q3dwebengineview import Q3DWebEngineView as Q3DView, Q3DWebEnginePage as Q3DWebPage

else:
    from .q3ddummyview import Q3DDummyView as Q3DView, Q3DDummyPage as Q3DWebPage
    logMessage("Both webkit widgets and web engine widgets modules not found. The preview gets disabled.")
