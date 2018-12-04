# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DInterface

                              -------------------
        begin                : 2018-11-09
        copyright            : (C) 2018 Minoru Akagi
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
from .conf import DEBUG_MODE
from .qgis2threejstools import logMessage


class Q3DInterface:

  def __init__(self, webPage, controller=None):
    self.webPage = webPage

    if controller:
      self.connectToController(controller)

  def connectToController(self, controller):
    self.controller = controller
    self.controller.connectToIface(self)

  def disconnectFromController(self):
    if self.controller:
      self.controller.disconnectFromIface()
    self.controller = None

  def startApplication(self, offScreen=False, exportMode=False):
    # configuration
    if exportMode:
      self.runScript("Q3D.Config.exportMode = true;")

    p = self.controller.settings.northArrow()
    if p.get("visible"):
      self.runScript("Q3D.Config.northArrow.visible = true;")
      self.runScript("Q3D.Config.northArrow.color = {};".format(p.get("color", 0)))

    header = self.controller.settings.headerLabel()
    footer = self.controller.settings.footerLabel()
    if header or footer:
      self.runScript('setHFLabel("{}", "{}");'.format(header.replace('"', '\\"'), footer.replace('"', '\\"')))

    # initialize app
    self.runScript("init({});".format("true" if offScreen else ""))

  def loadJSONObject(self, obj):
    # display the content of the object in the debug element
    if DEBUG_MODE == 2:
      self.runScript("document.getElementById('debug').innerHTML = '{}';".format(str(obj)[:500].replace("'", "\\'")))

    self.webPage.sendData(obj)

  def runScript(self, string, message=""):
    self.webPage.runScript(string, message, sourceID="q3dwindow.py")

  def loadScriptFile(self, filepath):
    self.webPage.loadScriptFile(filepath)

  def loadModelLoaders(self):
    self.webPage.loadModelLoaders()

  def abort(self):
    self.controller.abort()

  def settings(self):
    return self.controller.settings

  def buildScene(self, update_scene_settings=True, build_layers=True, update_extent=True, base64=False):
    self.controller.buildScene(update_scene_settings, build_layers, update_extent, base64)

  def buildLayer(self, layer):
    self.controller.buildLayer(layer)

  def showMessage(self, msg):
    logMessage(msg)

  def clearMessage(self):
    pass

  def progress(self, percentage=100, text=None):
    pass
