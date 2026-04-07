# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2015-09-14

import os
import shutil

from Qgis2threejs.utils import logger, pluginDir

MY_TEST_TEMPDIR = "E:/dev/qgis2threejs_test"


def testDir(*subdirs):
    return pluginDir("tests", *subdirs)


def dataPath(*subdirs):
    dataDir = testDir("data")
    if subdirs:
        return os.path.join(dataDir, *subdirs)
    return dataDir


def expectedDataPath(*subdirs):
    if os.path.exists(MY_TEST_TEMPDIR):
        dataDir = MY_TEST_TEMPDIR + "/expected"
    else:
        dataDir = testDir("expected")
        logger.warning("Expected data not exist.")      # TODO

    if subdirs:
        return os.path.join(dataDir, *subdirs)
    return dataDir


def outputPath(*subdirs):
    if os.path.exists(MY_TEST_TEMPDIR):
        dataDir = MY_TEST_TEMPDIR + "/output"
    else:
        dataDir = testDir("output")

    if subdirs:
        return os.path.join(dataDir, *subdirs)
    return dataDir


def initOutputDir(*subdirs):
    """initialize output directory"""
    out_dir = outputPath(*subdirs)
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)


def assertMessagesAppearInOrder(logs, expected):
    """check if expected messages appear in logs in order"""
    it = iter(logs)
    for msg in expected:
        for log in it:
            if msg in log:
                break
        else:
            assert False, f'"{msg}" not found in logs in order'
