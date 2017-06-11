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
import json
import os

from PyQt5.QtCore import QDir
from qgis.core import QgsMapLayer, QgsProject

from .datamanager import ImageManager, ModelManager
from .exportdem import DEMLayerExporter
from .exportvector import VectorLayerExporter
from .exportsettings import ExportSettings
from .qgis2threejscore import ObjectTreeItem
from .writer import ThreejsJSWriter, writeSphereTexture, writeSimpleDEM, writeMultiResDEM, writeVectors
from . import qgis2threejstools as tools
from .qgis2threejstools import getLayersInProject, logMessage
from .viewer2 import q3dconst

class ThreeJSExporter:

  def __init__(self, settings, progress=None):
    self.settings = settings
    self.progress = progress or dummyProgress
    self.imageManager = ImageManager(settings)
    self.clearBinaryData()

  def clearBinaryData(self):
    self.binaryData = {}
    #TODO: binary data -> something good for binary grid data, image data and model data (may be ascii file).

  def exportScene(self, export_layers=True):
    crs = self.settings.crs
    extent = self.settings.baseExtent
    rect = extent.unrotatedRect()
    mapTo3d = self.settings.mapTo3d()
    wgs84Center = self.settings.wgs84Center()

    obj = {
      "type": "scene",
      "properties": {
        "height": mapTo3d.planeHeight,
        "width": mapTo3d.planeWidth,
        "baseExtent": [rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()],
        "crs": str(crs.authid()),
        "proj": crs.toProj4(),
        "rotation": extent.rotation(),
        "wgs84Center": {
          "lat": wgs84Center.y(),
          "lon": wgs84Center.x()
          },
        "zExaggeration": mapTo3d.verticalExaggeration,
        "zShift": mapTo3d.verticalShift
        }
      }

    if export_layers:
      obj["layers"] = self.exportLayers()

    return obj

  def exportLayers(self):
    layers = []
    for index, layer in enumerate(self.settings.data["layers"]):
      if layer["geomType"] == q3dconst.TYPE_DEM:
        layers.append(self.exportDEMLayer(layer["layerId"], layer["properties"], layer["jsLayerId"]))
      else:
        layers.append(self.exportVectorLayer(layer["layerId"], layer["properties"], layer["jsLayerId"]))

    return layers

    #TODO: remove
    self.progress(5, "Writing DEM")

    # write primary DEM
    properties = self.settings.get(ObjectTreeItem.ITEM_DEM, {})
    primaryDEMLayerId = properties.get("comboBox_DEMLayer", 0)
    jsLayerId = primaryDEMLayerId
    layers.append(self.exportDEMLayer(primaryDEMLayerId, properties, jsLayerId))

    #self.binaryData[layerId] = bindata

    # write additional DEM(s)
    for layerId, properties in self.settings.get(ObjectTreeItem.ITEM_OPTDEM, {}).items():
      #TODO:
      # visible: initial visibility.
      # export: whether to export. True or False
      if properties.get("visible", False) and layerId != primaryDEMLayerId and QgsProject.instance().mapLayer(layerId):
        jsLayerId = layerId
        layers.append(self.exportDEMLayer(layerId, properties, jsLayerId))

    self.progress(30, "Writing vector data")

    # write vector data
    layerList = []
    # use vector layer order in project
    for layer in getLayersInProject():
      if layer.type() == QgsMapLayer.VectorLayer:
        parentId = ObjectTreeItem.parentIdByLayer(layer)
        properties = self.settings.get(parentId, {}).get(layer.id(), {})
        if properties.get("visible", False):
          layerList.append([layer.id(), properties])

    finishedLayers = 0
    for layerId, properties in layerList:
      mapLayer = QgsProject.instance().mapLayer(layerId)
      if mapLayer is None:
        continue

      self.progress(30 + 30 * finishedLayers / len(layerList), "Writing vector layer ({0} of {1}): {2}".format(finishedLayers + 1, len(layerList), mapLayer.name()))

      jsLayerId = layerId     #TODO: jsLayerId should be unique. layerId + number is preferable.
      layers.append(self.exportVectorLayer(layerId, properties, jsLayerId))
      finishedLayers += 1

    return layers

  def exportDEMLayer(self, layerId, properties, jsLayerId, visible=True):
    exporter = DEMLayerExporter(self.settings, self.imageManager)
    return exporter.export(layerId, properties, jsLayerId, visible)

  def exportVectorLayer(self, layerId, properties, jsLayerId, visible=True):
    exporter = VectorLayerExporter(self.settings, self.imageManager)
    return exporter.export(layerId, properties, jsLayerId, visible)


class ThreeJSFileExporter(ThreeJSExporter):

  def __init__(self, settings, progress=None):
    ThreeJSExporter.__init__(self, settings, progress)

    self.outDir = os.path.split(settings.htmlfilename)[0]

    self._index = -1

  def export(self):
    # read configuration of the template
    templateConfig = self.settings.templateConfig()
    templatePath = templateConfig["path"]

    # create output directory if not exists
    if not QDir(self.outDir).exists():
      QDir().mkpath(self.outDir)

    json_object = self.exportScene()
    #with open(self.settings.path_root + ".json", "w") as f:
    with open(os.path.join(self.outDir, "scene.json"), "w") as f:
      json.dump(json_object, f, indent=2)

    # TODO: export refdata (binary grid data, texture images and model data)
    self.progress(60, "Writing texture images")
    for layerId, dataset in self.binaryData.items():
      for suffix, data in dataset.items():
        with open(self.settings.path_root + suffix, "wb") as f:
          f.write(data)

    # copy files
    self.progress(90, "Copying library files")
    tools.copyFiles(self.filesToCopy(), self.outDir)

    # create html file
    options = []
    world = self.settings.get(ObjectTreeItem.ITEM_WORLD, {})
    if world.get("radioButton_Color", False):
      options.append("option.bgcolor = {0};".format(world.get("lineEdit_Color", 0)))

    # read html template
    with open(templatePath, "r", encoding="UTF-8") as f:
      html = f.read()

    html = html.replace("${title}", self.settings.title)
    html = html.replace("${controls}", '<script src="./threejs/%s"></script>' % self.settings.controls)    #TODO: move to self.scripts()
    html = html.replace("${options}", "\n".join(options))
    html = html.replace("${scripts}", "\n".join(self.scripts()))

    # write html
    with open(self.settings.htmlfilename, "w", encoding="UTF-8") as f:
      f.write(html)

    return True

  def nextLayerIndex(self):
    self._index += 1
    return self._index

  def exportDEMLayer(self, layerId, properties, jsLayerId, visible=True):
    title = "L{}".format(self.nextLayerIndex())
    pathRoot = os.path.join(self.outDir, title)
    urlRoot = "./" + title

    exporter = DEMLayerExporter(self.settings, self.imageManager)
    return exporter.export(layerId, properties, jsLayerId, visible, pathRoot, urlRoot)

  def exportVectorLayer(self, layerId, properties, jsLayerId, visible=True):
    title = "L{}".format(self.nextLayerIndex())
    pathRoot = os.path.join(self.outDir, title)
    urlRoot = "./" + title

    exporter = VectorLayerExporter(self.settings, self.imageManager)
    return exporter.export(layerId, properties, jsLayerId, visible, pathRoot, urlRoot)

  def filesToCopy(self):
    # three.js library
    files = [{"dirs": ["js/threejs"]}]

    # controls
    files.append({"files": ["js/threejs/controls/" + self.settings.controls], "dest": "threejs"})

    # template specific libraries (files)
    config = self.settings.templateConfig()

    for f in config.get("files", "").strip().split(","):
      p = f.split(">")
      fs = {"files": [p[0]]}
      if len(p) > 1:
        fs["dest"] = p[1]
      files.append(fs)

    for d in config.get("dirs", "").strip().split(","):
      p = d.split(">")
      ds = {"dirs": [p[0]], "subdirs": True}
      if len(p) > 1:
        ds["dest"] = p[1]
      files.append(ds)

    # proj4js
    if self.settings.coordsInWGS84:
      files.append({"dirs": ["js/proj4js"]})

    # model importer
    #TODO: files += self.modelManager.filesToCopy()

    return files

  def scripts(self):
    files = []      #TODO: self.modelManager.scripts()

    # proj4.js
    if self.settings.coordsInWGS84:    # display coordinates in latitude and longitude
      files.append("proj4js/proj4.js")

    # data files
    filetitle = self.settings.htmlfiletitle

    #if self.multiple_files:
    #  files += map(lambda x: "%s_%s.js" % (filetitle, x), range(self.jsfile_count))
    #else:
    files.append("%s.js" % filetitle)

    return ['<script src="./%s"></script>' % fn for fn in files]


def exportToThreeJS(settings, progress=None):
  exporter = ThreeJSFileExporter(settings, progress)
  exporter.export()


def dummyProgress(progress=None, statusMsg=None):
  pass
