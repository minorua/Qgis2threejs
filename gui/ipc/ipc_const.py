# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

class Event:

    # <- web page
    PAGE_LOAD_STARTED = "pageloadstart" # page loading started
    PAGE_LOADED = "pageloaded"          # page loading finished
    JS_ERROR_WARNING = "js_error"       # JavaScript error or warning: params={"is_error": bool}

    # <- web view
    DEV_TOOLS_CLOSED = "dev_closed"     # Developer tools closed
    PY_ERROR = "py_error"               # Python error: params={"msg": str}

    # <- IPC bridge
    METHOD_INVOKED = "invoke"           # bridge method invoked

    # <- window
    WND_STATE_CHANGED = "wnd_state_changed"     # window resized or moved

    # view proxy ->
    QUIT = "quit"                       # window is closing
    GPU_INFO = "gpuinfo"                # GPU Info menu item clicked
    DEV_TOOLS = "devtools"              # Developer tools menu item clicked
    CLICK = "click"                     # simulate a click for testing


class Request:

    # <- window
    EMBED_WND = "embed"
    WND_GEOM = "wnd_geom"

    # page proxy ->
    LOAD_DATA = "data"
    RELOAD = "reload"                   # reload page
    RUN_SCRIPT = "run"

    # view proxy ->
    SIZE = "size"
