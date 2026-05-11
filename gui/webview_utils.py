# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from .webview_conf import WEBVIEW_IN_QGIS_PROCESS

if WEBVIEW_IN_QGIS_PROCESS:
    from ..utils import pluginDir
    from ..utils.logging import logger, web_logger

else:
    import logging
    from ..conf import PLUGIN_NAME
    from ..preview.utils import pluginDir

    logger = logging.getLogger(PLUGIN_NAME)
    web_logger = logger
