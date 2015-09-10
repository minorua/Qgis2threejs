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
from PyQt4.QtCore import QSize
from qgis.core import QgsMapSettings, QgsRectangle

from export import exportToThreeJS
from exportsettings import ExportSettings
from rotatedrect import RotatedRect
import qgis2threejstools as tools


class Exporter:
  """a convenient class to export the scenes to web programmatically"""

  NO_ERROR = None

  def __init__(self, iface=None, settingsPath=None):
    """
    iface: QgisInterface
    settingsPath: unicode. Path to an existing settings file (.qto3settings).
    """
    self.iface = iface
    self.mapSettings = None

    # create an export settings object
    self.settings = ExportSettings()
    if settingsPath:
      self.settings.loadSettingsFromFile(settingsPath)

    if iface:
      self.mapSettings = iface.mapCanvas().mapSettings()
      self.settings.setMapSettings(self.mapSettings)

  def setCanvasSize(self, width, height):
    """
    width: float
    height: float
    """
    self.mapSettings.setOutputSize(QSize(width, height))
    self.settings.setMapSettings(self.mapSettings)

  def setExtent(self, center, width, height, rotation=0):
    """
    center: QgsPoint. In unit of project CRS.
    width: float. In unit of project CRS.
    height: float. In unit of project CRS.
    rotation: float. In degrees.
    """
    if self.mapSettings is None:
      self.mapSettings = QgsMapSettings()

    if rotation:
      rect = RotatedRect(center, width, height, rotation)
      rect.toMapSettings(self.mapSettings)
    else:
      rect = QgsRectangle(center.x() - width / 2, center.y() - height / 2,
                          center.x() + width / 2, center.y() + height / 2)
      self.mapSettings.setExtent(rect)

    self.settings.setMapSettings(self.mapSettings)

  def export(self, htmlPath, openBrowser=False):
    """
    htmlPath: unicode
    openBrowser: bool
    return value: 0 if success. Otherwise return error message.
    """
    self.settings.setOutputFilename(htmlPath)

    # check validity of export settings
    err_msg = self.settings.checkValidity()
    if err_msg:
      return err_msg

    ret = exportToThreeJS(self.settings, self.iface.legendInterface() if self.iface else None)
    if not ret:
      return "Failed to export (Unknown error)"

    if openBrowser:
      tools.openHTMLFile(self.settings.htmlfilename)

    return Exporter.NO_ERROR
