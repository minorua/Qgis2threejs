# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os


def pluginDir(*subdirs):
    p = os.path.dirname(os.path.dirname(__file__))
    if subdirs:
        return os.path.join(p, *subdirs)
    return p
