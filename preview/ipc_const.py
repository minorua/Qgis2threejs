# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

class Event:

    # <- web page
    PAGE_LOAD_STARTED = "pageloadstart" # page loading started
    PAGE_LOADED = "pageloaded"          # page loading finished
    JS_ERROR_WARNING = "js_error"       # JavaScript error or warning: params={"is_error": bool}

    # <- IPC bridge
    METHOD_INVOKED = "invoke"           # bridge method invoked

    # view proxy ->
    QUIT = "quit"                       # window is closing
    GPU_INFO = "gpuinfo"                # GPU Info menu item clicked
    DEV_TOOLS = "devtools"              # Developer tools menu item clicked
    CLICK = "click"                     # simulate a click for testing


class Request:

    # <- window
    EMBED_WND = "embed"

    # page proxy ->
    LOAD_DATA = "data"
    RELOAD = "reload"                   # reload page
    RUN_SCRIPT = "run"
