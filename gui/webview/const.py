# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

class WebViewType:
    NONE = 0
    WEBENGINE = 2


class WebViewMode:
    INPROCESS = 0
    EMBEDDED = 1
    SEPARATE = 2


class PreviewState:
    State_Idle = 0
    State_Loading = 1
    State_Error = 2
    State_Disabled = 3
