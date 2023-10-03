# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

from PyQt5.QtWidgets import QWidget
from .conf import PREFER_WEBKIT

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
    Q3DView = QWidget
