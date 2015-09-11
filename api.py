# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
        begin                : 2015-09-10
        copyright            : (C) 2015 Minoru Akagi
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
import qgis2threejstools


class Exporter:
  """A convenient class to export the scenes to web programmatically

  Attributes:
    settings: ExportSettings object
  """

  NO_ERROR = None

  def __init__(self, iface=None, settingsPath=None):
    """
    Args:
      iface: QgisInterface
        If specified, mapSettings attribute is initialized with the map settings of the map canvas.
        The iface.legendInterface() is used to export vector layers in the same order as the legend.

      settingsPath: unicode
        Path to an existing settings file (.qto3settings).
    """
    self.iface = iface
    self.mapSettings = None

    # create an export settings object
    self.settings = ExportSettings()
    if settingsPath:
      self.settings.loadSettingsFromFile(settingsPath)

    if iface:
      self.setMapSettings(iface.mapCanvas().mapSettings())

  def setExtent(self, center, width, height, rotation=0):
    """
    Args:
      center: QgsPoint. In unit of the map CRS.
      width: float. In unit of the map CRS.
      height: float. In unit of the map CRS.
      rotation: float. In degrees. (QGIS version >= 2.8)
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

  def setMapSettings(self, mapSettings):
    """
    Args:
      mapSettings: QgsMapSettings
    """
    self.mapSettings = mapSettings
    self.settings.setMapSettings(mapSettings)

  def export(self, htmlPath, openBrowser=False):
    """
    Args:
      htmlPath: unicode
        Output HTML file path.

      openBrowser: bool
        If True, open the exported page using default web browser.

    Returns:
      Exporter.NO_ERROR if success. Otherwise returns error message.
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
      qgis2threejstools.openHTMLFile(self.settings.htmlfilename)

    return Exporter.NO_ERROR
