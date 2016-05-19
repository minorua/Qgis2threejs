# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
        begin                : 2014-01-16
        copyright            : (C) 2014 Minoru Akagi
        email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import os
import codecs

from qgis.PyQt.QtCore import QDir
from qgis.core import QgsMapLayerRegistry


from .exportsettings import ExportSettings
from .qgis2threejscore import ObjectTreeItem
from .writer import ThreejsJSWriter, writeSphereTexture, writeSimpleDEM, writeMultiResDEM, writeVectors
from . import qgis2threejstools as tools

def exportToThreeJS(settings, legendInterface=None, objectTypeManager=None, progress=None):
  """legendInterface is used for vector layer ordering"""
  progress = progress or dummyProgress
  if objectTypeManager is None:
    from .vectorobject import ObjectTypeManager
    objectTypeManager = ObjectTypeManager()

  out_dir = os.path.split(settings.htmlfilename)[0]
  if not QDir(out_dir).exists():
    QDir().mkpath(out_dir)

  # ThreejsJSWriter object
  jsfilename = settings.path_root + ".js"
  f = codecs.open(jsfilename, "w", "UTF-8")
  writer = ThreejsJSWriter(f, settings, objectTypeManager)   #multiple_files=bool(settings.exportMode == ExportSettings.PLAIN_MULTI_RES))

  # read configuration of the template
  templateConfig = settings.templateConfig()
  templatePath = templateConfig["path"]

  if settings.exportMode == ExportSettings.SPHERE:
    # render texture for sphere and write it
    progress(5, "Rendering texture")
    writeSphereTexture(writer)
  else:
    # plain type
    writer.writeProject()
    progress(5, "Writing DEM")

    # write primary DEM
    demProperties = settings.get(ObjectTreeItem.ITEM_DEM, {})
    if settings.exportMode == ExportSettings.PLAIN_SIMPLE:
      writeSimpleDEM(writer, demProperties, progress)
    else:
      writeMultiResDEM(writer, demProperties, progress)

    # write additional DEM(s)
    primaryDEMLayerId = demProperties.get("comboBox_DEMLayer", 0)
    for layerId, properties in settings.get(ObjectTreeItem.ITEM_OPTDEM, {}).items():
      if properties.get("visible", False) and layerId != primaryDEMLayerId and QgsMapLayerRegistry.instance().mapLayer(layerId):
        writeSimpleDEM(writer, properties)

    progress(30, "Writing vector data")

    # write vector data
    writeVectors(writer, legendInterface, progress)

  # write images and model data
  progress(60, "Writing texture images")
  writer.writeImages()
  writer.writeModelData()
  f.close()

  progress(90, "Copying library files")

  # copy files
  tools.copyFiles(writer.filesToCopy(), out_dir)

  # generate html file
  options = []
  world = settings.get(ObjectTreeItem.ITEM_WORLD, {})
  if world.get("radioButton_Color", False):
    options.append("option.bgcolor = {0};".format(world.get("lineEdit_Color", 0)))

  # read html template
  with codecs.open(templatePath, "r", "UTF-8") as f:
    html = f.read()

  html = html.replace("${title}", settings.title)
  html = html.replace("${controls}", '<script src="./threejs/%s"></script>' % settings.controls)    #TODO: move to writer.scripts()
  html = html.replace("${options}", "\n".join(options))
  html = html.replace("${scripts}", "\n".join(writer.scripts()))

  # write html
  with codecs.open(settings.htmlfilename, "w", "UTF-8") as f:
    f.write(html)

  return True


def dummyProgress(progress=None, statusMsg=None):
  pass
