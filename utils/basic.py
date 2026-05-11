# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import configparser

from PyQt6.QtCore import QDir, QUuid

from ..conf import PLUGIN_NAME


### directory path ###
def pluginDir(*subdirs):
    p = os.path.dirname(os.path.dirname(__file__))
    if subdirs:
        return os.path.join(p, *subdirs)
    return p


def temporaryOutputDir(*subdirs):
    temp_dir = QDir.tempPath() + "/" + PLUGIN_NAME
    if subdirs:
        return os.path.join(temp_dir, *subdirs)
    return temp_dir


### conversion ###
def parseInt(string, def_val=None):
    try:
        return int(string)
    except (TypeError, ValueError):
        return def_val


def parseFloat(string, def_val=None):
    try:
        return float(string)
    except (TypeError, ValueError):
        return def_val


### template config ###
def templateDir():
    return pluginDir("web/html_templates")


def getTemplateConfig(template_path):
    """Read a template's .txt metadata file and return it as a dict.

    Args:
        template_path: Relative path to the template file.

    Returns:
        dict: Meta information (includes 'path' key with absolute template path).
    """
    abspath = os.path.join(templateDir(), template_path)
    meta_path = os.path.splitext(abspath)[0] + ".txt"

    if not os.path.exists(meta_path):
        return {}
    parser = configparser.ConfigParser()
    parser.read(meta_path)
    config = {"path": abspath}
    for item in parser.items("general"):
        config[item[0]] = item[1]

    return config


### Miscellaneous functions ###
def createUid():
    """Generate a short unique id."""
    return QUuid.createUuid().toString()[1:9]


def noop(*args, **kwargs):
    """A no-operation function that does nothing."""
    pass


class NoopClass:
    def __getattr__(self, name):
        def method(*args, **kwargs):
            return None
        return method
