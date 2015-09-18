# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SettingsDialog
                             -------------------
        begin                : 2014-01-10
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
import codecs
import ConfigParser
import os
from PyQt4.QtCore import Qt, QDir, QFile, QSettings
from PyQt4.QtGui import QDialog, QFileDialog, QAbstractItemView, QHeaderView, QTableWidgetItem

from ui.settingsdialog import Ui_SettingsDialog


class SettingsDialog(QDialog):

  def __init__(self, parent):
    QDialog.__init__(self, parent)

    # Set up the user interface from Designer.
    self.ui = ui = Ui_SettingsDialog()
    ui.setupUi(self)
    ui.lineEdit_BrowserPath.setPlaceholderText("Leave this empty to use your default browser")
    ui.toolButton_Browse.clicked.connect(self.browseClicked)

    # load settings
    settings = QSettings()
    ui.lineEdit_BrowserPath.setText(settings.value("/Qgis2threejs/browser", "", type=unicode))
    enabled_plugins = QSettings().value("/Qgis2threejs/plugins", "", type=unicode).split(",")

    # initialize plugin table widget
    plugin_dir = QDir(os.path.join(os.path.dirname(QFile.decodeName(__file__)), "plugins"))
    plugins = plugin_dir.entryList(QDir.Dirs | QDir.NoSymLinks | QDir.NoDotAndDotDot)

    tableWidget = ui.tableWidget_Plugins
    tableWidget.setRowCount(len(plugins))
    tableWidget.setColumnCount(1)
    tableWidget.setHorizontalHeaderLabels(["Name"])
    tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
    headerView = tableWidget.horizontalHeader()
    headerView.setResizeMode(0, QHeaderView.Stretch)

    self.plugin_metadata = []
    for i, name in enumerate(plugins):
      parser = ConfigParser.SafeConfigParser()
      with codecs.open(os.path.join(plugin_dir.absoluteFilePath(name), "metadata.txt"), "r", "UTF-8") as f:
        parser.readfp(f)

      metadata = dict(parser.items("general"))
      self.plugin_metadata.append(metadata)

      item = QTableWidgetItem(metadata.get("name", name))
      item.setCheckState(Qt.Checked if name in enabled_plugins else Qt.Unchecked)
      tableWidget.setItem(i, 0, item)

    tableWidget.selectionModel().currentRowChanged.connect(self.pluginSelectionChanged)

  def pluginSelectionChanged(self, current, previous):
    metadata = self.plugin_metadata[current.row()]
    self.ui.textBrowser_Plugin.setHtml(metadata.get("description"))

  def accept(self):
    settings = QSettings()

    # general settings
    settings.setValue("/Qgis2threejs/browser", self.ui.lineEdit_BrowserPath.text())

    # plugins
    enabled_plugins = []
    for i, metadata in enumerate(self.plugin_metadata):
      item = self.ui.tableWidget_Plugins.item(i, 0)
      if item.checkState() == Qt.Checked:
        enabled_plugins.append(metadata["id"])

    settings.setValue("/Qgis2threejs/plugins", ",".join(enabled_plugins))

    QDialog.accept(self)

  def browseClicked(self):
    filename = QFileDialog.getOpenFileName(self, self.tr("Select browser"))
    if filename != "":
      self.ui.lineEdit_BrowserPath.setText(filename)
