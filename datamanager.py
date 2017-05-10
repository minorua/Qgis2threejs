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

from qgis.PyQt.QtCore import Qt, QDir, QSize
from qgis.PyQt.QtGui import QColor, QImage, QPainter
from PyQt5.QtGui import QImageReader
from qgis.core import QgsMapLayer, QgsPalLabeling, QgsProject

from . import gdal2threejs
from . import qgis2threejstools as tools
from .qgis2threejstools import logMessage


class DataManager:
  """ manages a list of unique items """

  def __init__(self):
    self._list = []

  def _index(self, image):
    if image in self._list:
      return self._list.index(image)

    index = len(self._list)
    self._list.append(image)
    return index


class ImageManager(DataManager):

  IMAGE_FILE = 1
  CANVAS_IMAGE = 2
  MAP_IMAGE = 3
  LAYER_IMAGE = 4

  def __init__(self, exportSettings):
    DataManager.__init__(self)
    self.exportSettings = exportSettings
    self._renderer = None

  def imageIndex(self, path):
    img = (self.IMAGE_FILE, path)
    return self._index(img)

  def canvasImageIndex(self, transp_background):
    img = (self.CANVAS_IMAGE, transp_background)
    return self._index(img)

  def mapImageIndex(self, width, height, extent, transp_background):
    img = (self.MAP_IMAGE, (width, height, extent, transp_background))
    return self._index(img)

  def layerImageIndex(self, layerids, width, height, extent, transp_background):
    img = (self.LAYER_IMAGE, (layerids, width, height, extent, transp_background))
    return self._index(img)

  def mapCanvasImage(self, transp_background=False):
    """ returns base64 encoded map canvas image """
    canvas = self.exportSettings.canvas
    if canvas is None or transp_background or True:   #TODO: canvas.map() has been removed
      size = self.exportSettings.mapSettings.outputSize()
      return self.renderedImage(size.width(), size.height(), self.exportSettings.baseExtent, transp_background)

    return tools.base64image(canvas.map().contentImage())

  def saveMapCanvasImage(self):
    if self.exportSettings.canvas is None:
      return
    texfilename = self.exportSettings.path_root + ".png"
    self.exportSettings.canvas.saveAsImage(texfilename)
    tools.removeTemporaryFiles([texfilename + "w"])

  def _initRenderer(self):
    # set up a renderer
    labeling = QgsPalLabeling()
    renderer = QgsMapRenderer()
    renderer.setDestinationCrs(self.exportSettings.crs)
    renderer.setProjectionsEnabled(True)
    renderer.setLabelingEngine(labeling)

    # save renderer
    self._labeling = labeling
    self._renderer = renderer

  def renderedImage(self, width, height, extent, transp_background=False, layerids=None):

    # render layers with QgsMapRendererCustomPainterJob
    from qgis.core import QgsMapRendererCustomPainterJob
    antialias = True
    settings = self.exportSettings.mapSettings

    # store old map settings
    old_outputSize = settings.outputSize()
    old_extent = settings.extent()
    old_rotation = settings.rotation()
    old_layerids = settings.layerIds()
    old_backgroundColor = settings.backgroundColor()

    # map settings
    settings.setOutputSize(QSize(width, height))
    settings.setExtent(extent.unrotatedRect())
    settings.setRotation(extent.rotation())

    if layerids:
      settings.setLayers(tools.getLayersByLayerIds(layerids))

    if transp_background:
      settings.setBackgroundColor(QColor(Qt.transparent))
    #else:    #TODO: remove
      #settings.setBackgroundColor(self.exportSettings.canvas.canvasColor())

    has_pluginlayer = False
    for layer in settings.layers():
      if layer and layer.type() == QgsMapLayer.PluginLayer:
        has_pluginlayer = True
        break

    # create an image
    image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
    painter = QPainter()
    painter.begin(image)
    if antialias:
      painter.setRenderHint(QPainter.Antialiasing)

    # rendering
    job = QgsMapRendererCustomPainterJob(settings, painter)
    if has_pluginlayer:
      job.renderSynchronously()   # use this method so that TileLayerPlugin layer is rendered correctly
    else:
      job.start()
      job.waitForFinished()
    painter.end()

    # restore map settings
    settings.setOutputSize(old_outputSize)
    settings.setExtent(old_extent)
    settings.setRotation(old_rotation)
    settings.setLayers(tools.getLayersByLayerIds(old_layerids))
    settings.setBackgroundColor(old_backgroundColor)

    return tools.base64image(image)

    #if exportSettings.localBrowsingMode:
    #else:
    #  texfilename = os.path.splitext(htmlfilename)[0] + "_%d.png" % plane_index
    #  image.save(texfilename)
    #  texSrc = os.path.split(texfilename)[1]
    #  tex["src"] = texSrc

  def write(self, f):   #TODO: separated image files (not in localBrowsingMode)
    if len(self._list) == 0:
      return

    f.write('\n// Base64 encoded images\n')
    for index, image in enumerate(self._list):
      imageType = image[0]
      if imageType == self.IMAGE_FILE:
        image_path = image[1]

        exists = os.path.exists(image_path)
        if exists and os.path.isfile(image_path):
          size = QImageReader(image_path).size()
          args = (index, size.width(), size.height(), gdal2threejs.base64image(image_path))
        else:
          f.write("project.images[%d] = {data:null};\n" % index)

          if exists:
            err_msg = "Not image file path"
          else:
            err_msg = "Image file not found"
          logMessage("{0}: {1}".format(err_msg, image_path))
          continue

      elif imageType == self.MAP_IMAGE:
        width, height, extent, transp_background = image[1]
        args = (index, width, height, self.renderedImage(width, height, extent, transp_background))

      elif imageType == self.LAYER_IMAGE:
        layerids, width, height, extent, transp_background = image[1]
        args = (index, width, height, self.renderedImage(width, height, extent, transp_background, layerids))

      else:   #imageType == self.CANVAS_IMAGE:
        transp_background = image[1]
        size = self.exportSettings.mapSettings.outputSize()
        args = (index, size.width(), size.height(), self.mapCanvasImage(transp_background))

      f.write('project.images[%d] = {width:%d,height:%d,data:"%s"};\n' % args)


class MaterialManager(DataManager):

  MESH_LAMBERT = 0
  MESH_PHONG = 1
  LINE_BASIC = 2
  SPRITE = 3

  WIREFRAME = 10
  MESH_LAMBERT_SMOOTH = 0
  MESH_LAMBERT_FLAT = 11

  CANVAS_IMAGE = 20
  MAP_IMAGE = 21
  LAYER_IMAGE = 22
  IMAGE_FILE = 23

  ERROR_COLOR = "0"

  def __init__(self):
    DataManager.__init__(self)
    self.writtenCount = 0

  def _indexCol(self, type, color, transparency=0, doubleSide=False):
    if color[0:2] != "0x":
      color = self.ERROR_COLOR
    mat = (type, color, transparency, doubleSide)
    return self._index(mat)

  def getMeshLambertIndex(self, color, transparency=0, doubleSide=False):
    return self._indexCol(self.MESH_LAMBERT, color, transparency, doubleSide)

  def getSmoothMeshLambertIndex(self, color, transparency=0, doubleSide=False):
    return self._indexCol(self.MESH_LAMBERT_SMOOTH, color, transparency, doubleSide)

  def getFlatMeshLambertIndex(self, color, transparency=0, doubleSide=False):
    return self._indexCol(self.MESH_LAMBERT_FLAT, color, transparency, doubleSide)

  def getLineBasicIndex(self, color, transparency=0):
    return self._indexCol(self.LINE_BASIC, color, transparency)

  def getWireframeIndex(self, color, transparency=0):
    return self._indexCol(self.WIREFRAME, color, transparency)

  def getCanvasImageIndex(self, transparency=0, transp_background=False):
    mat = (self.CANVAS_IMAGE, transp_background, transparency, True)
    return self._index(mat)

  def getMapImageIndex(self, width, height, extent, transparency=0, transp_background=False):
    mat = (self.MAP_IMAGE, (width, height, extent, transp_background), transparency, True)
    return self._index(mat)

  def getLayerImageIndex(self, layerids, width, height, extent, transparency=0, transp_background=False):
    mat = (self.LAYER_IMAGE, (layerids, width, height, extent, transp_background), transparency, True)
    return self._index(mat)

  def getImageFileIndex(self, path, transparency=0, transp_background=False, doubleSide=False):
    mat = (self.IMAGE_FILE, (path, transp_background), transparency, doubleSide)
    return self._index(mat)

  def getSpriteIndex(self, path, transparency=0):
    transp_background = True
    mat = (self.SPRITE, (path, transp_background), transparency, False)
    return self._index(mat)

  def write(self, f, imageManager):
    if len(self._list) <= self.writtenCount:
      return

    toMaterialType = {self.WIREFRAME: self.MESH_LAMBERT,
                      self.MESH_LAMBERT_FLAT: self.MESH_LAMBERT,
                      self.CANVAS_IMAGE: self.MESH_PHONG,
                      self.MAP_IMAGE: self.MESH_PHONG,
                      self.LAYER_IMAGE: self.MESH_PHONG,
                      self.IMAGE_FILE: self.MESH_PHONG}

    for mat in self._list[self.writtenCount:]:
      m = {"type": toMaterialType.get(mat[0], mat[0])}

      transp_background = False

      if mat[0] == self.CANVAS_IMAGE:
        transp_background = mat[1]
        m["i"] = imageManager.canvasImageIndex(transp_background)
      elif mat[0] == self.MAP_IMAGE:
        width, height, extent, transp_background = mat[1]
        m["i"] = imageManager.mapImageIndex(width, height, extent, transp_background)
      elif mat[0] == self.LAYER_IMAGE:
        layerids, width, height, extent, transp_background = mat[1]
        m["i"] = imageManager.layerImageIndex(layerids, width, height, extent, transp_background)
      elif mat[0] in [self.IMAGE_FILE, self.SPRITE]:
        filepath, transp_background = mat[1]
        m["i"] = imageManager.imageIndex(filepath)
      else:
        m["c"] = mat[1]

      if transp_background:
        m["t"] = 1

      if mat[0] == self.WIREFRAME:
        m["w"] = 1

      if mat[0] == self.MESH_LAMBERT_FLAT:
        m["flat"] = 1

      transparency = mat[2]
      if transparency > 0:
        opacity = 1.0 - transparency / 100
        m["o"] = opacity

      # double sides
      if mat[3]:
        m["ds"] = 1

      index = self.writtenCount
      f.write("lyr.m[{0}] = {1};\n".format(index, tools.pyobj2js(m, quoteHex=False)))
      self.writtenCount += 1


class ModelManager(DataManager):

  def __init__(self):
    DataManager.__init__(self)
    self._collada = False

  def modelIndex(self, path, model_type="JSON"):
    if model_type == "COLLADA":
      self._collada = True

    model = (model_type, path)
    return self._index(model)

  def filesToCopy(self):
    f = []
    if self._collada:
      f.append({"files": ["js/threejs/loaders/ColladaLoader.js"], "dest": "threejs/loaders"})
    return f

  def scripts(self):
    s = []
    if self._collada:
      s.append("threejs/loaders/ColladaLoader.js")
    return s

  def write(self, f):
    if len(self._list) == 0:
      return

    f.write('\n// 3D model data\n')
    for index, model in enumerate(self._list):
      model_type, path = model
      exists = os.path.exists(path)
      if exists and os.path.isfile(path):
        with open(path) as model_file:
          data = model_file.read().replace("\\", "\\\\").replace("'", "\\'").replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n")
        f.write("project.models[%d] = {type:'%s',data:'%s'};\n" % (index, model_type, data))
      else:
        f.write("project.models[%d] = {type:'%s',data:null};\n" % (index, model_type))

        if exists:
          err_msg = "Not 3D model file path"
        else:
          err_msg = "3D model file not found"
        logMessage("{0}: {1} ({2})".format(err_msg, path, model_type))
