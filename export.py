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
import json
import os

from PyQt5.QtCore import QDir, QEventLoop, QFileInfo, QSize
from PyQt5.QtGui import QImage, QPainter

from .conf import DEBUG_MODE
from .build import ThreeJSBuilder
from .builddem import DEMLayerBuilder
from .buildvector import VectorLayerBuilder
from .buildpointcloud import PointCloudLayerBuilder
from .exportsettings import ExportSettings
from .q3dcontroller import Q3DController
from .q3dinterface import Q3DInterface
from .q3dview import Q3DWebPage
from . import q3dconst
from . import qgis2threejstools as tools


class ThreeJSExporter(ThreeJSBuilder):

    def __init__(self, settings=None, progress=None, logMessage=None):
        ThreeJSBuilder.__init__(self, settings or ExportSettings(), progress, logMessage)

        self._index = -1

        self.modelManagers = []

    def loadSettings(self, filename=None):
        self.settings.loadSettingsFromFile(filename)

    def setMapSettings(self, settings):
        self.settings.setMapSettings(settings)

    def export(self, filename=None, cancelSignal=None):
        if filename:
            self.settings.setOutputFilename(filename)

        config = self.settings.templateConfig()

        # create output data directory if not exists
        dataDir = self.settings.outputDataDirectory()
        if not QDir(dataDir).exists():
            QDir().mkpath(dataDir)

        # export the scene and its layers
        json_object = self.buildScene()
        if self.settings.localMode:
            with open(os.path.join(dataDir, "scene.js"), "w", encoding="utf-8") as f:
                f.write("app.loadJSONObject(")
                json.dump(json_object, f, indent=2)
                f.write(");")
        else:
            with open(os.path.join(dataDir, "scene.json"), "w", encoding="utf-8") as f:
                json.dump(json_object, f, indent=2 if DEBUG_MODE else None)

        # copy files
        self.progress(90, "Copying library files...")
        tools.copyFiles(self.filesToCopy(), self.settings.outputDirectory())

        # options in html file
        options = []

        sp = self.settings.sceneProperties()
        if sp.get("checkBox_autoZShift"):
            options.append("Q3D.Config.autoZShift = true;")

        if sp.get("radioButton_Color"):
            options.append("Q3D.Config.bgColor = {0};".format(sp.get("colorButton_Color", 0)))

        # camera
        if self.settings.isOrthoCamera():
            options.append("Q3D.Config.orthoCamera = true;")

        # web export options
        opts = self.settings.options()
        if opts:
            for key in opts:
                options.append("Q3D.Config.{0} = {1};".format(key, tools.pyobj2js(self.settings.option(key))))

        # North arrow
        p = self.settings.decorationProperties("NorthArrow")
        if p.get("visible"):
            options.append("Q3D.Config.northArrow.visible = true;")
            options.append("Q3D.Config.northArrow.color = {0};".format(p.get("color", 0)))

        # read html template
        with open(config["path"], "r", encoding="utf-8") as f:
            html = f.read()

        title = self.settings.outputFileTitle()
        mapping = {
            "title": title,
            "options": "\n".join(options),
            "scripts": "\n".join(self.scripts()),
            "scenefile": "./data/{0}/scene.{1}".format(title, "js" if self.settings.localMode else "json"),
            "header": self.settings.headerLabel(),
            "footer": self.settings.footerLabel()
        }
        for key, value in mapping.items():
            html = html.replace("${" + key + "}", value)

        # write to html file
        with open(self.settings.outputFileName(), "w", encoding="utf-8") as f:
            f.write(html)

    def nextLayerIndex(self):
        self._index += 1
        return self._index

    def buildLayer(self, layer):
        title = tools.abchex(self.nextLayerIndex())

        if self.settings.localMode:
            pathRoot = urlRoot = None
        else:
            pathRoot = os.path.join(self.settings.outputDataDirectory(), title)
            urlRoot = "./data/{0}/{1}".format(self.settings.outputFileTitle(), title)

        if layer.geomType == q3dconst.TYPE_DEM:
            builder = DEMLayerBuilder(self.settings, self.imageManager, layer, pathRoot, urlRoot, logMessage=self.logMessage)
        elif layer.geomType == q3dconst.TYPE_POINTCLOUD:
            builder = PointCloudLayerBuilder(self.settings, layer, logMessage=self.logMessage)
        else:
            builder = VectorLayerBuilder(self.settings, self.imageManager, layer, pathRoot, urlRoot, logMessage=self.logMessage)
            self.modelManagers.append(builder.modelManager)
        return builder.build(True)

    def filesToCopy(self):
        # three.js library
        files = [{"dirs": ["js/threejs"]}]

        # controls
        files.append({"files": ["js/threejs/controls/" + self.settings.controls()], "dest": "threejs"})

        # template specific libraries (files)
        config = self.settings.templateConfig()
        for f in config.get("files", "").strip().split(","):
            p = f.split(">")
            fs = {"files": [p[0]]}
            if len(p) > 1:
                fs["dest"] = p[1]
            files.append(fs)

        for d in config.get("dirs", "").strip().split(","):
            p = d.split(">")
            ds = {"dirs": [p[0]], "subdirs": True}
            if len(p) > 1:
                ds["dest"] = p[1]
            files.append(ds)

        # proj4js
        if self.settings.coordsInWGS84():
            files.append({"dirs": ["js/proj4js"]})

        # layer-specific dependencies
        for layer in [lyr for lyr in self.settings.getLayerList() if lyr.visible]:  # HACK: lyr.export
            if layer.geomType == q3dconst.TYPE_POINTCLOUD:
                files.append({"dirs": ["js/potree-core"], "subdirs": True})
                files.append({"files": ["js/pointcloudlayer.js"]})
                break

        # model loades and model files
        for manager in self.modelManagers:
            for f in manager.filesToCopy():
                if f not in files:
                    files.append(f)

        return files

    def scripts(self):
        files = []

        # three.js and controls
        files.append("./threejs/three.min.js")
        files.append("./threejs/{}".format(self.settings.controls()))

        # html template config
        config = self.settings.templateConfig()
        s = config.get("scripts", "").strip()
        if s:
            files += s.split(",")

        # proj4.js
        if self.settings.coordsInWGS84():    # display coordinates in latitude and longitude
            proj4 = "./proj4js/proj4.js"
            if proj4 not in files:
                files.append(proj4)

        # Qgis2threejs.js
        files.append("./Qgis2threejs.js")

        # layer-specific dependencies
        for layer in [lyr for lyr in self.settings.getLayerList() if lyr.visible]:
            if layer.geomType == q3dconst.TYPE_POINTCLOUD:
                files.append("./potree-core/potree.min.js")
                files.append("./pointcloudlayer.js")
                break

        # model loaders
        for manager in self.modelManagers:
            for f in manager.scripts():
                if f not in files:
                    files.append(f)

        return ['<script src="%s"></script>' % fn for fn in files]


class BridgeExporterBase:

    def __init__(self, settings=None):
        self.settings = settings or ExportSettings()
        self.controller = Q3DController(self.settings)
        self.exportMode = False

        self.page = Q3DWebPage()
        self.iface = Q3DInterface(self.settings, self.page)
        self.controller.connectToIface(self.iface)

    def loadSettings(self, filename=None):
        self.settings.loadSettingsFromFile(filename)

    def setMapSettings(self, settings):
        self.settings.setMapSettings(settings)

    def initWebPage(self, width, height):
        loop = QEventLoop()
        self.page.ready.connect(loop.quit)
        self.page.setViewportSize(QSize(width, height))

        if self.page.mainFrame().url().isEmpty():
            self.page.setup(self.settings, exportMode=self.exportMode)
        else:
            self.page.reload()

        loop.exec_()

    def mkdir(self, filename):
        dir = QFileInfo(filename).dir()
        if not dir.exists():
            QDir().mkpath(dir.absolutePath())


class ImageExporter(BridgeExporterBase):

    def render(self, cameraState=None, cancelSignal=None):
        if self.page is None:
            return QImage(), "page not ready"

        # set camera position and camera target
        if cameraState:
            self.page.setCameraState(cameraState)

        # build scene
        self.controller.buildScene(update_extent=False)

        err = self.page.waitForSceneLoaded(cancelSignal)

        # header and footer labels
        self.page.runScript('setHFLabel("{}", "{}");'.format(self.settings.headerLabel().replace('"', '\\"'),
                                                             self.settings.footerLabel().replace('"', '\\"')))
        # render scene
        size = self.page.viewportSize()
        image = QImage(size.width(), size.height(), QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        self.page.mainFrame().render(painter)
        painter.end()
        return image, err

    def export(self, filename, cameraState=None, cancelSignal=None):
        # prepare output directory
        self.mkdir(filename)

        image, err = self.render(cameraState, cancelSignal)
        image.save(filename)
        return err


class ModelExporter(BridgeExporterBase):

    def __init__(self, settings=None):
        super().__init__(settings)
        self.exportMode = True

    def initWebPage(self, width, height):
        super().initWebPage(width, height)
        self.page.loadScriptFile(q3dconst.SCRIPT_GLTFEXPORTER)

    def export(self, filename, cancelSignal=None):
        if self.page is None:
            return "page not ready"

        # prepare output directory
        self.mkdir(filename)

        # build scene
        self.controller.buildScene(update_extent=False, base64=True)

        err = self.page.waitForSceneLoaded(cancelSignal)

        # save model
        self.page.runScript("saveModelAsGLTF('{0}');".format(filename.replace("\\", "\\\\")))

        return err
