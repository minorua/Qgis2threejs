# -*- coding: utf-8 -*-
# (C) 2017 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2017-06-11

import os
from datetime import datetime

from PyQt5.QtCore import Qt, QDir, QEventLoop, QUrl
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.core import QgsApplication, QgsProject

from .conf import PLUGIN_NAME
from .export import ThreeJSExporter
from .utils import getTemplateConfig, openUrl, templateDir, temporaryOutputDir
from .ui.exporttowebdialog import Ui_ExportToWebDialog


class ExportToWebDialog(QDialog):

    def __init__(self, settings, page, parent=None):
        QDialog.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)

        self.settings = settings
        self.page = page
        self.logHtml = ""
        self.logNextIndex = 1
        self.warnings = 0

        self.ui = Ui_ExportToWebDialog()
        self.ui.setupUi(self)

        # general settings
        fn = settings.outputFileName()
        self.ui.lineEdit_OutputDir.setText(os.path.dirname(fn))

        bn = os.path.basename(fn)
        self.ui.lineEdit_Filename.setText(bn or "index.html")

        title = settings.title() or QgsProject.instance().title() or QgsProject.instance().baseName() or os.path.splitext(bn)[0]
        self.ui.lineEdit_Title.setText(title)

        self.ui.checkBox_PreserveViewpoint.setChecked(bool(settings.option("viewpoint")))
        self.ui.checkBox_LocalMode.setChecked(bool(settings.option("localMode")))

        # template settings
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

        for key, value in settings.options().items():
            if key == "gui.customPlane":
                self.ui.checkBox_Plane.setChecked(True)

            if key == "AR.MND":
                self.ui.lineEdit_MND.setText(str(value))

        # animation
        anm = settings.animationData()
        self.ui.groupBox_Animation.setChecked(anm.get("enabled", False))
        self.ui.checkBox_StartOnLoad.setChecked(anm.get("startOnLoad", False))

        self.ui.comboBox_Template.currentIndexChanged.connect(self.templateChanged)
        self.ui.pushButton_Browse.clicked.connect(self.browseClicked)

        self.ui.textBrowser.setOpenLinks(False)
        self.ui.textBrowser.anchorClicked.connect(openUrl)

    def templateChanged(self, index=None):
        # update settings widget visibility
        config = getTemplateConfig(self.ui.comboBox_Template.currentData())
        optset = set(config.get("options", "").split(","))
        optset.discard("")

        b = "gui.customPlane" in optset
        for w in [self.ui.label_Plane, self.ui.checkBox_Plane]:
            w.setVisible(b)

        b = "AR.MND" in optset
        for w in [self.ui.label_MND, self.ui.lineEdit_MND, self.ui.label_MND2]:
            w.setVisible(b)

        anim = bool(config.get("animation", "yes") == "yes")
        self.ui.groupBox_Animation.setEnabled(anim)

    def browseClicked(self):
        # directory select dialog
        d = self.ui.lineEdit_OutputDir.text() or QDir.homePath()
        d = QFileDialog.getExistingDirectory(self, self.tr("Select Output Directory"), d)
        if d:
            self.ui.lineEdit_OutputDir.setText(d)

    def accept(self):
        """export"""

        self.settings.clearOptions()

        # general settings
        out_dir = self.ui.lineEdit_OutputDir.text()
        is_temporary = (out_dir == "")
        if is_temporary:
            out_dir = temporaryOutputDir()
            # title, ext = os.path.splitext(filename)
            # filename = title + datetime.today().strftime("%Y%m%d%H%M%S") + ext

        filename = self.ui.lineEdit_Filename.text()
        if not filename.strip():
            filename = "index.html"
        elif not filename.lower().endswith((".html", ".htm")):
            filename += ".html"

        filepath = os.path.join(out_dir, filename)
        if not is_temporary and os.path.exists(filepath):
            if QMessageBox.question(self, PLUGIN_NAME, "The HTML file already exists. Do you want to overwrite it?", QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
                return

        self.settings.setOutputFilename("" if is_temporary else filepath)
        self.settings.setTitle(self.ui.lineEdit_Title.text())

        if self.ui.checkBox_PreserveViewpoint.isChecked():
            self.settings.setOption("viewpoint", self.page.cameraState())

        local_mode = self.ui.checkBox_LocalMode.isChecked()
        if local_mode:
            self.settings.setOption("localMode", True)

        # template settings
        self.settings.setTemplate(self.ui.comboBox_Template.currentData())

        options = self.settings.templateConfig().get("options", "")
        if options:
            optlist = options.split(",")

            if "gui.customPlane" in optlist and self.ui.checkBox_Plane.isChecked():
                self.settings.setOption("gui.customPlane", True)

            if "AR.MND" in optlist:
                try:
                    self.settings.setOption("AR.MND", float(self.ui.lineEdit_MND.text()))
                except Exception as e:
                    QMessageBox.warning(self, PLUGIN_NAME, "Invalid setting value for M.N. direction. Must be a numeric value.")
                    return

        # animation settings
        anim_enabled = self.ui.groupBox_Animation.isEnabled() and self.ui.groupBox_Animation.isChecked()
        startOnLoad = self.ui.checkBox_StartOnLoad.isChecked()

        # save checked states to settings
        keyframeData = self.settings.animationData()
        keyframeData["enabled"] = anim_enabled
        keyframeData["startOnLoad"] = startOnLoad

        if anim_enabled:
            self.settings.setOption("animation.enabled", True)

            if startOnLoad:
                self.settings.setOption("animation.startOnLoad", True)

            if keyframeData.get("repeat"):
                self.settings.setOption("animation.repeat", True)

        # make a copy of export settings
        settings = self.settings.clone()

        settings.isPreview = False
        settings.localMode = settings.jsonSerializable = local_mode

        err_msg = settings.checkValidity()
        if err_msg:
            QMessageBox.warning(self, PLUGIN_NAME, err_msg or "Invalid settings")
            return

        for w in [self.ui.tabSettings, self.ui.pushButton_Export, self.ui.pushButton_Close]:
            w.setEnabled(False)

        self.ui.tabWidget.setCurrentIndex(1)

        self.logHtml = """
<style>
div.progress {margin-top:10px;}
div.warning {font-weight:bold;}
div.indented {margin-left:3em;}
th {text-align:left;}
</style>
"""
        self.logNextIndex = 1
        self.warnings = 0

        self.progress(0, "Export started.")
        t0 = datetime.now()

        # export
        exporter = ThreeJSExporter(settings, self.progressNumbered, self.logMessageIndented)
        completed = exporter.export(filepath, cancelSignal=self.ui.pushButton_Cancel.clicked)

        elapsed = datetime.now() - t0

        for w in [self.ui.tabSettings, self.ui.pushButton_Export, self.ui.pushButton_Close]:
            w.setEnabled(True)

        if not completed:
            self.progress(100, "<br>Export has been canceled.")
            self.ui.progressBar.setValue(0)
            return

        msg = "<br><a name='complete'>Export has been completed in {:,.2f} seconds.</a>".format(elapsed.total_seconds())
        if self.warnings:
            msg += "<br><b>There {} during the export. See above.</b>".format("was a warning" if self.warnings == 1 else "were {} warnings".format(self.warnings))
        self.progress(100, msg)

        data_dir = settings.outputDataDirectory()

        url_dir = QUrl.fromLocalFile(out_dir)
        url_data = QUrl.fromLocalFile(data_dir)
        url_scene = QUrl.fromLocalFile(os.path.join(data_dir, "scene.js" if local_mode else "scene.json"))
        url_page = QUrl.fromLocalFile(filepath)

        self.logHtml += """
<br>
<table>
<tr><th>Output directory</th><td><a href="{}">{}</a></td></tr>
<tr><th>Data directory</th><td><a href="{}">{}</a></td></tr>
<tr><th>Scene file</th><td>{}</td></tr>
<tr><th>Web page file</th><td><a href="{}">{}</a></td></tr>
</table>
""".format(url_dir.toString(), url_dir.toLocalFile(),
           url_data.toString(), url_data.toLocalFile(),
                                url_scene.toLocalFile(),
           url_page.toString(), url_page.toLocalFile())

        self.ui.textBrowser.setHtml(self.logHtml)
        self.ui.textBrowser.scrollToAnchor("complete")

    def progress(self, percentage=None, msg=None, numbered=False):
        if percentage is not None:
            self.ui.progressBar.setValue(percentage)

            v = bool(percentage != 100)
            self.ui.progressBar.setEnabled(v)
            self.ui.pushButton_Cancel.setEnabled(v)

        if msg:
            if numbered:
                msg = "{}. {}".format(self.logNextIndex, msg)
                self.logNextIndex += 1
            self.logHtml += "<div class='progress'>{}</div>".format(msg)
            self.ui.textBrowser.setHtml(self.logHtml)

        QgsApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

    def progressNumbered(self, percentage=None, msg=None):
        self.progress(percentage, msg, numbered=True)

    def log(self, msg, warning=False, indented=False):
        if warning:
            self.warnings += 1

        classes = (["warning"] if warning else []) + (["indented"] if indented else [])

        self.logHtml += "<div{}>{}</div>".format(" class='{}'".format(" ".join(classes)) if classes else "", msg)
        self.ui.textBrowser.setHtml(self.logHtml)

        QgsApplication.processEvents(QEventLoop.ExcludeUserInputEvents)

    def logMessageIndented(self, msg, warning=False):
        self.log(msg, warning, indented=True)
