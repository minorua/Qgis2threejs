# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ExportToWebDialog

                              -------------------
        begin                : 2017-06-11
        copyright            : (C) 2017 Minoru Akagi
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
from PyQt5.QtCore import Qt, QDir
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox

from .export import ThreeJSExporter
from .qgis2threejstools import getTemplateConfig, logMessage, openHTMLFile, templateDir, temporaryOutputDir
from .ui.exporttowebdialog import Ui_ExportToWebDialog


class ExportToWebDialog(QDialog):

    def __init__(self, settings, page, parent=None):
        QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.settings = settings
        self.page = page

        self.ui = Ui_ExportToWebDialog()
        self.ui.setupUi(self)

        # output directory
        self.ui.lineEdit_OutputDir.setText(os.path.dirname(settings.outputFileName()))

        # template combo box
        cbox = self.ui.comboBox_Template
        for i, entry in enumerate(QDir(templateDir()).entryList(["*.html", "*.htm"])):
            config = getTemplateConfig(entry)
            cbox.addItem(config.get("name", entry), entry)

            # set tool tip text
            desc = config.get("description", "")
            if desc:
                cbox.setItemData(i, desc, Qt.ToolTipRole)

        index = cbox.findData(settings.template())
        if index != -1:
            cbox.setCurrentIndex(index)

        self.templateChanged()

        # general settings
        self.ui.checkBox_PreserveViewpoint.setChecked(bool(settings.option("viewpoint")))

        # template settings
        for key, value in settings.options().items():
            if key == "AR.MND":
                self.ui.lineEdit_MND.setText(str(value))

        self.ui.comboBox_Template.currentIndexChanged.connect(self.templateChanged)
        self.ui.pushButton_Browse.clicked.connect(self.browseClicked)
        self.ui.pushButton_Export.clicked.connect(self.exportClicked)
        self.ui.pushButton_Cancel.clicked.connect(self.close)

    def templateChanged(self, index=None):
        # update settings widget visibility
        config = getTemplateConfig(self.ui.comboBox_Template.currentData())
        optset = set(config.get("options", "").split(","))
        optset.discard("")

        # template settings group box
        self.ui.groupBox_Template.setVisible(bool(optset))

        if optset:
            for widget in [self.ui.label_MND, self.ui.lineEdit_MND]:
                widget.setVisible("AR.MND" in optset)

    def browseClicked(self):
        # directory select dialog
        d = self.ui.lineEdit_OutputDir.text() or QDir.homePath()
        d = QFileDialog.getExistingDirectory(self, self.tr("Select Output Directory"), d)
        if d:
            self.ui.lineEdit_OutputDir.setText(d)

    def exportClicked(self):
        # template
        self.settings.setTemplate(self.ui.comboBox_Template.currentData())

        self.settings.clearOptions()
        # save general settings
        if self.ui.checkBox_PreserveViewpoint.isChecked():
            self.settings.setOption("viewpoint", self.page.cameraState())

        # save template settings
        options = self.settings.templateConfig().get("options", "")
        if options:
            optlist = options.split(",")

            if "AR.MND" in optlist:
                try:
                    self.settings.setOption("AR.MND", float(self.ui.lineEdit_MND.text()))
                except Exception as e:
                    QMessageBox.warning(self, "Qgis2threejs", "Invalid setting value for M.N. direction. Must be a numeric value.")
                    return

        # output html file name
        out_dir = self.ui.lineEdit_OutputDir.text()
        filename = self.ui.lineEdit_Filename.text()
        is_temporary = (out_dir == "")
        if is_temporary:
            out_dir = temporaryOutputDir()
            #title, ext = os.path.splitext(filename)
            #filename = title + datetime.today().strftime("%Y%m%d%H%M%S") + ext

        filepath = os.path.join(out_dir, filename)
        if not is_temporary and os.path.exists(filepath):
            if QMessageBox.question(self, "Qgis2threejs", "The HTML file already exists. Do you want to overwrite it?", QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
                return

        self.settings.setOutputFilename(filepath)

        err_msg = self.settings.checkValidity()
        if err_msg is not None:
            QMessageBox.warning(self, "Qgis2threejs", err_msg or "Invalid settings")
            return

        self.ui.pushButton_Export.setEnabled(False)
        self.progress(0)

        # export
        exporter = ThreeJSExporter(self.settings, self.progress)
        exporter.export()

        self.progress(100)

        if is_temporary:
            self.settings.setOutputFilename("")

        # store last settings
        # settings = QSettings()
        # settings.setValue("/Qgis2threejs/lastTemplate", self.settings.templatePath)

        if self.ui.checkBox_openPage.isChecked():
            if not openHTMLFile(filepath):
                return

        self.close()

    def progress(self, percentage=None, statusMsg=None):
        # TODO: [Web export] progress
        pass
