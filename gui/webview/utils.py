# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from .conf import WEBVIEW_IN_QGIS_PROCESS

if WEBVIEW_IN_QGIS_PROCESS:
    from ...utils.logging import logger, web_logger

else:
    import logging
    from ...conf import PLUGIN_NAME

    logger = logging.getLogger(PLUGIN_NAME)
    web_logger = logger
