# -*- coding: utf-8 -*-
"""
author : Minoru Akagi
begin  : 2015-09-14

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""
import os
import shutil
import sys

from PyQt4.QtCore import qDebug


def pluginPath(subdir=None):
  tests_dir = os.path.dirname(os.path.abspath(__file__).decode(sys.getfilesystemencoding()))
  plugin_dir = os.path.dirname(tests_dir)
  if subdir is None:
    return plugin_dir
  return os.path.join(plugin_dir, subdir)


def dataPath(subdir=None):
  data_path = pluginPath(os.path.join("tests", "data"))
  if subdir is None:
    return data_path
  return os.path.join(data_path, subdir)


def outputDataPath(subdir=None):
  data_path = pluginPath(os.path.join("tests", "output"))
  if subdir is None:
    return data_path
  return os.path.join(data_path, subdir)


def initOutputDir():
  """initialize output directory"""
  out_dir = outputDataPath()
  if os.path.exists(out_dir):
    shutil.rmtree(out_dir)
  os.mkdir(out_dir)


def log(msg):
  if isinstance(msg, unicode):
    qDebug(msg.encode("utf-8"))
  else:
    qDebug(str(msg))
