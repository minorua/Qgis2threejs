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

from .datamanager import ImageManager, ModelManager
from .exportdem import DEMLayerExporter
from .exportvector import VectorLayerExporter
from . import q3dconst
from . import qgis2threejstools as tools

class ThreeJSExporter:

  def __init__(self, settings, progress=None):
    self.settings = settings
    self.progress = progress or dummyProgress
    self.imageManager = ImageManager(settings)

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
    for layer in self.settings.getLayerList():
      if layer.visible:
        layers.append(self.exportLayer(layer))
    return layers

  def exportLayer(self, layer):
    if layer.geomType == q3dconst.TYPE_DEM:
      exporter = DEMLayerExporter(self.settings, self.imageManager, layer)
    else:
      exporter = VectorLayerExporter(self.settings, self.imageManager, layer)
    return exporter.build()

  def exporters(self, layer):
    if layer.geomType == q3dconst.TYPE_DEM:
      exporter = DEMLayerExporter(self.settings, self.imageManager, layer)
    else:
      exporter = VectorLayerExporter(self.settings, self.imageManager, layer)
    yield exporter

    for blockExporter in exporter.blocks():
      yield blockExporter


class ThreeJSFileExporter(ThreeJSExporter):

  def __init__(self, settings, progress=None):
    ThreeJSExporter.__init__(self, settings, progress)

    self._index = -1

  def export(self):
    self.settings.setTemplatePath("3DViewer.html");   # this is a temporal line

    # read configuration of the template
    templateConfig = self.settings.templateConfig()
    templatePath = templateConfig["path"]

    # create output data directory if not exists
    if not QDir(self.settings.outputdatadir).exists():
      QDir().mkpath(self.settings.outputdatadir)

    # write scene data to a file in json format
    json_object = self.exportScene()
    with open(os.path.join(self.settings.outputdatadir, "scene.json"), "w") as f:
      json.dump(json_object, f, indent=2)

    # copy files
    self.progress(90, "Copying library files")
    tools.copyFiles(self.filesToCopy(), self.settings.outputdir)

    # options in html file
    options = []
    world = self.settings.get(self.settings.WORLD, {})
    if world.get("radioButton_Color", False):
      options.append("option.bgcolor = {0};".format(world.get("lineEdit_Color", 0)))

    # read html template
    with open(templatePath, "r", encoding="UTF-8") as f:
      html = f.read()

    mapping = {
      "title": self.settings.htmlfiletitle,
      "controls": '<script src="./threejs/%s"></script>' % self.settings.controls(),
      "options": "\n".join(options),
      "scripts": "\n".join(self.scripts()),
      "scenefile": "./data/{0}/scene.json".format(self.settings.htmlfiletitle)
      }
    for key, value in mapping.items():
      html = html.replace("${" + key + "}", value)

    # write to html file
    with open(self.settings.htmlfilename, "w", encoding="UTF-8") as f:
      f.write(html)

    return True

  def nextLayerIndex(self):
    self._index += 1
    return self._index

  def exportLayer(self, layer):
    title = "L{0}".format(self.nextLayerIndex())
    pathRoot = os.path.join(self.settings.outputdatadir, title)
    urlRoot = "./data/{0}/{1}".format(self.settings.htmlfiletitle, title)

    if layer.geomType == q3dconst.TYPE_DEM:
      exporter = DEMLayerExporter(self.settings, self.imageManager, layer, pathRoot, urlRoot)
    else:
      exporter = VectorLayerExporter(self.settings, self.imageManager, layer, pathRoot, urlRoot)
    return exporter.build(True)

  def filesToCopy(self):
    # three.js library
    files = [{"dirs": ["js/threejs"]}]

    # controls
    files.append({"files": ["js/threejs/controls/" + self.settings.controls()], "dest": "threejs"})

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
    if self.settings.coordsInWGS84():
      files.append({"dirs": ["js/proj4js"]})

    # model importer
    #TODO: [Model] files += self.modelManager.filesToCopy()

    return files

  def scripts(self):
    files = []      #TODO: [Model] self.modelManager.scripts()

    # proj4.js
    if self.settings.coordsInWGS84():    # display coordinates in latitude and longitude
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
