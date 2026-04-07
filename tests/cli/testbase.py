# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from ..utils import initOutputDir, outputPath

MANUAL_PAGE_CHECK = True
MANUAL_IMAGE_CHECK = True


class CLITestBase:

    PROJ_FILE = "testproject1/testproject1.qgs"
    SETTING_FILE = "testproject1/scene1.qto3settings"

    @classmethod
    def initOutputDir(cls):
        initOutputDir(cls.__name__[4:])

    @classmethod
    def outputPath(cls, *subdirs):
        return outputPath(cls.__name__[4:], *subdirs)
