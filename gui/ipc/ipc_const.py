# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

class Event:

    # <- web page
    PAGE_LOAD_STARTED = "pageloadstart" # page loading started
    PAGE_LOADED = "pageloaded"          # page loading finished
    JS_ERROR_WARNING = "js_error"       # JavaScript error or warning: params={"isError": bool, "message": str, "lineNumber": int, "sourceID": str}

    # <- web view
    DEV_TOOLS_CLOSED = "dev_closed"     # Developer tools closed
    PY_ERROR = "py_error"               # Python error: params={"msg": str}

    # <- IPC bridge
    METHOD_INVOKED = "invoke"           # bridge method invoked

    # <- window
    WND_GEOM_CHANGED = "wnd_geom_changed"     # window resized or moved


class Command:

    # <- window
    EMBED_WND = "embed"

    # page proxy ->
    LOAD_DATA = "data"                  # load data immediately or enqueue data
    REMOVE_LAYER_DATA = "rmlyr"         # remove queued data related to layer from send queue
    CLEAR_QUEUE = "clrq"                # clear send queue

    RELOAD = "reload"                   # reload page

    # view proxy ->
    DEV_TOOLS = "devtools"              # show developer tools
    GPU_INFO = "gpuinfo"                # show GPU info
    QUIT = "quit"                       # close window

    # testing ->
    RESIZE = "resize"


class Request:

    # <- web
    TILE_DATA = "tiledata"

    # page proxy ->
    RUN_SCRIPT = "run"

    # view proxy ->
    SIZE = "size"
