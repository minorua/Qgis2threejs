# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import json
import os

from qgis.PyQt.QtCore import QDir, QEventLoop, QFileInfo, QSize
from qgis.PyQt.QtGui import QImage, QPainter

from .conf import DEBUG_MODE, PLUGIN_VERSION
from .build import ThreeJSBuilder
from .builddem import DEMLayerBuilder
from .buildvector import VectorLayerBuilder
from .buildpointcloud import PointCloudLayerBuilder
from .exportsettings import ExportSettings
from .q3dcontroller import Q3DController
from .q3dconst import LayerType, Script
from .q3dinterface import Q3DInterface
from .q3dview import Q3DWebPage
from .utils import hex_color
from . import utils


class ThreeJSExporter(ThreeJSBuilder):

    def __init__(self, settings=None, progress=None, log=None):
        ThreeJSBuilder.__init__(self, settings or ExportSettings(), progress, log)

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
        json_object = self.buildScene(cancelSignal=cancelSignal)

        if self.canceled:
            return False

        # animation
        if self.settings.isAnimationEnabled():
            json_object["animation"] = self.settings.animationData(export=True, warning_log=self.warning_log)

        if self.settings.localMode:
            with open(os.path.join(dataDir, "scene.js"), "w", encoding="utf-8") as f:
                f.write("app.loadJSONObject(")
                json.dump(json_object, f, indent=2)
                f.write('); window.setTimeout(function () { app.dispatchEvent({type: "sceneLoaded"}); }, 0);')
        else:
            with open(os.path.join(dataDir, "scene.json"), "w", encoding="utf-8") as f:
                json.dump(json_object, f, indent=2 if DEBUG_MODE else None)

        narration = self.settings.narrations(warning_log=self.warning_log)

        # copy files
        files = narration["files"]
        if files:
            self.progress(90, "Copying image files used in narrative content...")

            img_dir = os.path.join(self.settings.outputDataDirectory(), "img")
            QDir().mkpath(img_dir)

            for f in files:
                if utils.copyFile(f, os.path.join(img_dir, os.path.basename(f)), overwrite=True):
                    self.log("Copied {}.".format(f))
                else:
                    self.log("Failed to copy {}.".format(f), warning=True)

        self.progress(95, "Copying library files...")
        utils.copyFiles(self.filesToCopy(), self.settings.outputDirectory())

        # options in html file
        options = []

        # scene
        sp = self.settings.sceneProperties()
        if sp.get("radioButton_Color"):
            options.append("Q3D.Config.bgColor = {0};".format(hex_color(sp.get("colorButton_Color", 0), prefix="0x")))

        if not self.settings.coordDisplay():
            options.append("Q3D.Config.coord.visible = false;")

        if self.settings.isCoordLatLon():
            options.append("Q3D.Config.coord.latlon = true;")

        # camera
        if self.settings.isOrthoCamera():
            options.append("Q3D.Config.orthoCamera = true;")

        # web export options
        opts = self.settings.options()
        if opts:
            for key in opts:
                options.append("Q3D.Config.{0} = {1};".format(key, utils.pyobj2js(self.settings.option(key))))

        # North arrow
        p = self.settings.widgetProperties("NorthArrow")
        if p.get("visible"):
            options.append("Q3D.Config.northArrow.enabled = true;")
            options.append("Q3D.Config.northArrow.color = {0};".format(hex_color(p.get("color", 0), prefix="0x")))

        # read html template
        with open(config["path"], "r", encoding="utf-8") as f:
            html = f.read()

        mapping = {
            "title": self.settings.title(),
            "options": "\n".join(options),
            "scripts": "\n".join(self.scripts()),
            "scenefile": "./data/{0}/scene.{1}".format(self.settings.outputFileTitle(), "js" if self.settings.localMode else "json"),
            "header": self.settings.headerLabel(),
            "footer": self.settings.footerLabel(),
            "narration": narration["html"],
            "version": PLUGIN_VERSION
        }
        for key, value in mapping.items():
            html = html.replace("${" + key + "}", value)

        # write to html file
        with open(self.settings.outputFileName(), "w", encoding="utf-8") as f:
            f.write(html)

        return True

    def nextLayerIndex(self):
        self._index += 1
        return self._index

    def buildLayer(self, layer, cancelSignal=None):
        title = utils.abchex(self.nextLayerIndex())

        if self.settings.localMode:
            pathRoot = urlRoot = None
        else:
            pathRoot = os.path.join(self.settings.outputDataDirectory(), title)
            urlRoot = "./data/{0}/{1}".format(self.settings.outputFileTitle(), title)

        layer = layer.clone()
        layer.opt.allMaterials = True

        if layer.type == LayerType.DEM:
            builder = DEMLayerBuilder(self.settings, layer, self.imageManager, pathRoot, urlRoot, log=self.log)
        elif layer.type == LayerType.POINTCLOUD:
            builder = PointCloudLayerBuilder(self.settings, layer, log=self.log)
        else:
            builder = VectorLayerBuilder(self.settings, layer, self.imageManager, pathRoot, urlRoot, log=self.log)
            self.modelManagers.append(builder.modelManager)
        return builder.build(True, cancelSignal)

    def filesToCopy(self):
        # three.js library
        files = [{"dirs": ["js/threejs"]}]

        # controls
        files.append({"files": ["js/threejs/controls/" + self.settings.controls()], "dest": "threejs"})

        if self.settings.isNavigationEnabled():
            files.append({"files": ["js/threejs/editor/ViewHelper.js"], "dest": "threejs"})

        # outline effect
        if self.settings.useOutlineEffect():
            files.append({"files": ["js/threejs/effects/OutlineEffect.js"], "dest": "threejs"})

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
        if self.settings.isCoordLatLon():
            files.append({"dirs": ["js/proj4js"]})

        # layer-specific dependencies
        wl = pc = True
        for layer in [lyr for lyr in self.settings.layers() if lyr.visible]:  # HACK: lyr.export
            if layer.type == LayerType.LINESTRING:
                if layer.properties.get("comboBox_ObjectType") == "Thick Line" and wl:
                    files.append({"dirs": ["js/meshline"]})
                    wl = False

            elif layer.type == LayerType.POINTCLOUD and pc:
                files.append({"dirs": ["js/potree-core"], "subdirs": True})
                files.append({"files": ["js/pointcloudlayer.js"]})
                pc = False

        # model loades and model files
        for manager in self.modelManagers:
            for f in manager.filesToCopy():
                if f not in files:
                    files.append(f)

        # animation
        if self.settings.isAnimationEnabled():
            files.append({"dirs": ["js/tweenjs"]})

        return files

    def scripts(self):
        files = []

        # three.js and controls
        files.append("./threejs/three.min.js")
        files.append("./threejs/{}".format(self.settings.controls()))

        if self.settings.isNavigationEnabled():
            files.append("./threejs/ViewHelper.js")

        # outline effect
        if self.settings.useOutlineEffect():
            files.append("./threejs/OutlineEffect.js")

        # html template config
        config = self.settings.templateConfig()
        s = config.get("scripts", "").strip()
        if s:
            files += s.split(",")

        # proj4.js
        if self.settings.isCoordLatLon():    # display coordinates in latitude and longitude format
            proj4 = "./proj4js/proj4.js"
            if proj4 not in files:
                files.append(proj4)

        # animation
        if self.settings.isAnimationEnabled():
            files.append("./tweenjs/tween.js")

        # Qgis2threejs.js
        files.append("./Qgis2threejs.js")

        # layer-specific dependencies
        wl = pc = True
        for layer in [lyr for lyr in self.settings.layers() if lyr.visible]:
            if layer.type == LayerType.LINESTRING:
                if layer.properties.get("comboBox_ObjectType") == "Thick Line" and wl:
                    files.append("./meshline/THREE.MeshLine.js")
                    wl = False
            elif layer.type == LayerType.POINTCLOUD and pc:
                files.append("./potree-core/potree.min.js")
                files.append("./pointcloudlayer.js")
                pc = False

        # model loaders
        for manager in self.modelManagers:
            for f in manager.scripts():
                if f not in files:
                    files.append(f)

        return ['<script src="%s"></script>' % fn for fn in files]

    def warning_log(self, msg):
        self.log(msg, warning=True)


class BridgeExporterBase:

    def __init__(self, settings=None):
        self.settings = settings or ExportSettings()
        self.settings.isPreview = True

        self.page = Q3DWebPage()
        self.iface = Q3DInterface(self.settings, self.page)
        self.iface.statusMessage.connect(self.iface.showStatusMessage)

        self.controller = Q3DController(self.settings)
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
            self.page.setup(self.settings)
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
        self.page.runScript('setHFLabel(pyData())', data=self.settings.widgetProperties("Label"))

        # render scene
        size = self.page.viewportSize()
        image = QImage(size.width(), size.height(), QImage.Format.Format_ARGB32_Premultiplied)
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
        self.settings.jsonSerializable = True

    def initWebPage(self, width, height):
        super().initWebPage(width, height)
        self.page.loadScriptFile(Script.GLTFEXPORTER)

    def export(self, filename, cancelSignal=None):
        if self.page is None:
            return "page not ready"

        # prepare output directory
        self.mkdir(filename)

        # build scene
        self.controller.buildScene(update_extent=False)

        err = self.page.waitForSceneLoaded(cancelSignal)

        # save model
        self.page.runScript("saveModelAsGLTF('{0}')".format(filename.replace("\\", "\\\\")))

        return err
