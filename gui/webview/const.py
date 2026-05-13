# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

class WebViewType:
    NONE = 0
    WEBENGINE = 2


class WebViewMode:
    INPROCESS = 0       # In-process preview mode (native)
    EMBEDDED = 1        # Embedded external-process preview mode
    SEPARATE = 2        # Separate external-process preview mode


class PreviewState:
    State_Idle = 0
    State_Loading = 1
    State_Error = 2
    State_Disabled = 3
