# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-10

from configparser import ConfigParser
import os
from qgis.PyQt.QtCore import Qt, QDir, QSettings
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QAbstractItemView, QHeaderView, QTableWidgetItem

from .ui.settingsdialog import Ui_SettingsDialog
from ..utils import logger, pluginDir


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
        plugins = plugin_dir.entryList(QDir.Filter.Dirs | QDir.Filter.NoSymLinks | QDir.Filter.NoDotAndDotDot)

        tableWidget = ui.tableWidget_Plugins
        tableWidget.setColumnCount(1)
        tableWidget.setHorizontalHeaderLabels(["Name"])
        tableWidget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        headerView = tableWidget.horizontalHeader()
        headerView.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.plugin_metadata = []
        for i, name in enumerate(plugins):
            if name[0] == "_":    # skip __pycache__ dir.
                continue

            parser = ConfigParser()
            try:
                with open(os.path.join(plugin_dir.absoluteFilePath(name), "metadata.txt"), "r", encoding="utf-8") as f:
                    parser.read_file(f)

                metadata = dict(parser.items("general"))
                self.plugin_metadata.append(metadata)
            except Exception as e:
                logger.error("Unable to read metadata of plugin: {} ({})".format(name, e))

        tableWidget.setRowCount(len(self.plugin_metadata))
        for i, metadata in enumerate(self.plugin_metadata):
            item = QTableWidgetItem(metadata.get("name", name))
            item.setCheckState(Qt.CheckState.Checked if name in enabled_plugins else Qt.CheckState.Unchecked)
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
            if item.checkState() == Qt.CheckState.Checked:
                enabled_plugins.append(metadata["id"])

        settings.setValue("/Qgis2threejs/plugins", ",".join(enabled_plugins))

        QDialog.accept(self)

    def browseClicked(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.tr("Select browser"))
        if filename != "":
            self.ui.lineEdit_BrowserPath.setText(filename)
