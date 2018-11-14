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

  def startApplication(self):
    # configuration
    p = self.controller.settings.northArrow()
    if p.get("visible"):
      self.runString("Q3D.Config.northArrow.visible = true;")
      self.runString("Q3D.Config.northArrow.color = {};".format(p.get("color", 0)))

    label = self.controller.settings.footerLabel()
    if label:
      self.runString('setFooterLabel("{}");'.format(label.replace('"', '\\"')))

    # initialize app
    self.runString("init();")

  def loadJSONObject(self, obj):
    # display the content of the object in the debug element
    if DEBUG_MODE == 2:
      self.runString("document.getElementById('debug').innerHTML = '{}';".format(str(obj)[:500].replace("'", "\\'")))

    self.webPage.sendData(obj)

  def runString(self, string, message=""):
    self.webPage.runString(string, message, sourceID="q3dwindow.py")

  def loadScriptFile(self, filepath):
    self.webPage.loadScriptFile(filepath)

  def loadModelLoaders(self):
    self.webPage.loadModelLoaders()

  def abort(self):
    self.controller.abort()

  def updateScene(self, base64=False):
    self.controller.updateScene(base64=base64)

  def updateLayer(self, layer):
    self.controller.updateLayer(layer)

  def showMessage(self, msg):
    logMessage(msg)

  def clearMessage(self):
    pass

  def progress(self, percentage=100, text=None):
    pass
