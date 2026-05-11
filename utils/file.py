# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import shutil

from PyQt6.QtCore import QDir, QFile, QFileInfo

from .basic import pluginDir, temporaryOutputDir
from .logging import logger


### File and directory related functions ###
def copyFile(source, dest, overwrite=False):
    if os.path.exists(dest):
        if overwrite or abs(QFileInfo(source).lastModified().secsTo(QFileInfo(dest).lastModified())) > 5:   # use secsTo for different file systems
            QFile.remove(dest)
            logger.debug("Existing file removed: %s", dest)
        else:
            logger.info("File already exists: %s", dest)
            return False

    ret = QFile.copy(source, dest)
    if ret:
        logger.debug("File copied: %s to %s", source, dest)
    else:
        logger.warning("Failed to copy file: %s to %s", source, dest)
    return ret


def copyDir(source, dest, overwrite=False):
    if os.path.exists(dest):
        if overwrite:
            shutil.rmtree(dest)
            logger.debug("Existing dir removed: %s", dest)
        else:
            logger.info("Dir already exists: %s", dest)
            return False

    shutil.copytree(source, dest)
    logger.debug("Dir copied: %s to %s", source, dest)
    return True


def copyFiles(filesToCopy, out_dir):
    """Copies the specified files and directories to the specified output directory.

    Args:
        filesToCopy (list): A list of dict objects that define the copy targets.
            Each dict can contain the following keys:
                - "files": A list of file paths to copy. If a relative path is given, it is relative to the plugin directory.
                - "dirs": A list of directory paths to copy. If a relative path is given, it is relative to the plugin directory.
                - "dest": The name of the subdirectory within the output directory to copy into.
                           If omitted, files are copied directly under `out_dir`.
                - "subdirs": If True, copy directories recursively.
                              If False, copy only files directly under the directory.
                              Optional. Default is False.
                - "overwrite": If True, overwrite existing files or directories when copying.
                                Optinal. Default is False.
        out_dir (str): The root directory where files and directories are copied to.
    """
    plugin_dir = pluginDir()
    for item in filesToCopy:
        dest_dir = os.path.join(out_dir, item.get("dest", ""))
        subdirs = item.get("subdirs", False)
        overwrite = item.get("overwrite", False)

        logger.debug("copying %s to %s", item, dest_dir)

        # make destination directory
        QDir().mkpath(dest_dir)

        # copy files
        for f in item.get("files", []):
            fi = QFileInfo(f)
            dest = os.path.join(dest_dir, fi.fileName())
            if fi.isRelative():
                copyFile(os.path.join(plugin_dir, f), dest, overwrite)
            else:
                copyFile(f, dest, overwrite)

        # copy directories
        for d in item.get("dirs", []):
            fi = QFileInfo(d)
            source = os.path.join(plugin_dir, d) if fi.isRelative() else d
            dest = os.path.join(dest_dir, fi.fileName())
            if subdirs:
                copyDir(source, dest, overwrite)
            else:
                # make destination directory
                QDir().mkpath(dest)

                # copy files in the source directory
                filenames = QDir(source).entryList(QDir.Filter.Files)
                for filename in filenames:
                    copyFile(os.path.join(source, filename), os.path.join(dest, filename), overwrite)


def removeDir(dirName):
    d = QDir(dirName)
    if d.exists():
        for info in d.entryInfoList(QDir.Filter.Dirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot):
            if info.isDir():
                removeDir(info.absoluteFilePath())
            else:
                d.remove(info.fileName())
        d.rmdir(dirName)


def removeTemporaryFiles(filelist):
    """Remove a list of temporary files."""
    for file in filelist:
        QFile.remove(file)


def removeTemporaryOutputDir():
    removeDir(temporaryOutputDir())
