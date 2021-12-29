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
import configparser
import os
from PyQt5.QtCore import Qt, QDir, QSettings
from PyQt5.QtWidgets import QDialog, QFileDialog, QAbstractItemView, QHeaderView, QTableWidgetItem

from .tools import logMessage, pluginDir
from .ui.settingsdialog import Ui_SettingsDialog


class SettingsDialog(QDialog):

    def __init__(self, parent):
        QDialog.__init__(self, parent)

        # Set up the user interface from Designer.
        self.ui = ui = Ui_SettingsDialog()
        ui.setupUi(self)
        ui.lineEdit_BrowserPath.setPlaceholderText("Leave this empty to use your default browser")
        ui.pushButton_Browse.clicked.connect(self.browseClicked)

        # load settings
        settings = QSettings()
        ui.lineEdit_BrowserPath.setText(settings.value("/Qgis2threejs/browser", "", type=str))
        enabled_plugins = QSettings().value("/Qgis2threejs/plugins", "", type=str).split(",")

        # initialize plugin table widget
        plugin_dir = QDir(pluginDir("plugins"))
        plugins = plugin_dir.entryList(QDir.Dirs | QDir.NoSymLinks | QDir.NoDotAndDotDot)

        tableWidget = ui.tableWidget_Plugins
        tableWidget.setColumnCount(1)
        tableWidget.setHorizontalHeaderLabels(["Name"])
        tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
        headerView = tableWidget.horizontalHeader()
        headerView.setSectionResizeMode(QHeaderView.Stretch)

        self.plugin_metadata = []
        for i, name in enumerate(plugins):
            if name[0] == "_":    # skip __pycache__ dir.
                continue

            parser = configparser.SafeConfigParser()
            try:
                with open(os.path.join(plugin_dir.absoluteFilePath(name), "metadata.txt"), "r", encoding="utf-8") as f:
                    parser.readfp(f)

                metadata = dict(parser.items("general"))
                self.plugin_metadata.append(metadata)
            except Exception as e:
                logMessage("Unable to read metadata of plugin: {} ({})".format(name, e))

        tableWidget.setRowCount(len(self.plugin_metadata))
        for i, metadata in enumerate(self.plugin_metadata):
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
        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select browser"))
        if filename != "":
            self.ui.lineEdit_BrowserPath.setText(filename)
