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
import os
try:
  from qgis.core import QgsMapSettings, QgsRectangle

  from .export import exportToThreeJS
  from .exportsettings import ExportSettings
  from .rotatedrect import RotatedRect
  from . import qgis2threejstools

except ImportError:
  if os.environ.get('READTHEDOCS', None) is None:  # and os.environ.get('SPHINXBUILD', None) is None:
    raise


class Exporter:
  """A convenient class to export the scenes to web programmatically
  """

  NO_ERROR = None

  def __init__(self, iface=None, settingsPath=None):
    """ Constructor.

      :param iface: If specified, mapSettings attribute is initialized with the map settings of the map canvas.
                    The iface.legendInterface() is used to export vector layers in the same order as the legend.
      :type iface: QgisInterface
      :param settingsPath: Path to an existing settings file (.qto3settings).
      :type settingsPath: unicode
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
    """ Set map extent to export settings.

    This is a convenience method to set map extent to export settings.
    Map settings should be set before this method is called.

    :param center: Center of the map extent in the map CRS.
    :type center: QgsPoint
    :param width: Width of the map extent in unit of the map CRS.
    :type width: float
    :param height: Height of the map extent in unit of the map CRS.
    :type height: float
    :param rotation: Rotation in degrees. Requires QGIS version 2.8 or later.
    :type rotation: float
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
    """Set map settings to export settings.

    Map settings is used to define base extent of the export and render a map canvas image.

    :param mapSettings: Map settings to be set.
    :type mapSettings: QgsMapSettings
    """
    self.mapSettings = mapSettings
    self.settings.setMapSettings(mapSettings)

  def export(self, htmlPath, openBrowser=False):
    """Do export.

    :param htmlPath: Output HTML file path.
    :type htmlPath: unicode
    :param openBrowser: If True, open the exported page using default web browser.
    :type openBrowser: bool

    :returns: Exporter.NO_ERROR if success. Otherwise returns error message.
    :rtype: None or unicode.
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
