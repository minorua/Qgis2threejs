# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtGui import QImageWriter


def canSaveAsWebP():
    return b"webp" in QImageWriter.supportedImageFormats()
