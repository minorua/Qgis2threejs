# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import json
import os

from qgis.PyQt.QtCore import QDir, QEventLoop, QFileInfo, QSize, QTimer
from qgis.PyQt.QtGui import QImage, QPainter

from ..build.builder import ThreeJSBuilder, LayerBuilderFactory
from ..build.vector.builder import VectorLayerBuilder
from ..const import LayerType, ScriptFile
from ..exportsettings import ExportSettings
from ..controller.controller import Q3DController
from ..controller.interface import Q3DInterface
from ...conf import DEBUG_MODE, PLUGIN_VERSION
from ...gui import webview
from ...utils import hex_color, logger
from ... import utils


class ThreeJSExporter(ThreeJSBuilder):
    """Exporter class for generating a set of files for a three.js-based 3D scene
    viewable in external web browsers.
    """

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
        data = self.buildScene(cancelSignal=cancelSignal)

        if self.canceled:
            return False

        # animation
        if self.settings.isAnimationEnabled():
            data["animation"] = self.settings.animationData(export=True, warning_log=self.warning_log)

        if self.settings.localMode:
            with open(os.path.join(dataDir, "scene.js"), "w", encoding="utf-8") as f:
                f.write("app.loadData(")
                json.dump(data, f, indent=2)
                f.write('); window.setTimeout(function () { app.dispatchEvent({type: "sceneLoaded"}); }, 0);')
        else:
            with open(os.path.join(dataDir, "scene.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2 if DEBUG_MODE else None)

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

        builder_cls = LayerBuilderFactory.get(layer.type, VectorLayerBuilder)
        builder = builder_cls(self.settings, layer, self.imageManager, pathRoot, urlRoot, log=self.log)
        if builder_cls == VectorLayerBuilder:
            self.modelManagers.append(builder.modelManager)
        return builder.build(True, cancelSignal)

    def filesToCopy(self):
        # three.js library
        files = [{"dirs": ["web/js/lib/threejs"]}]

        # controls
        files.append({"files": ["web/js/lib/threejs/controls/" + self.settings.controls()], "dest": "threejs"})

        if self.settings.isNavigationEnabled():
            files.append({"files": ["web/js/lib/threejs/editor/ViewHelper.js"], "dest": "threejs"})

        # outline effect
        if self.settings.useOutlineEffect():
            files.append({"files": ["web/js/lib/threejs/effects/OutlineEffect.js"], "dest": "threejs"})

        # template specific files
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
            files.append({"dirs": ["web/js/lib/proj4js"]})

        # layer-specific dependencies
        wl = pc = True
        for layer in [lyr for lyr in self.settings.layers() if lyr.visible]:  # HACK: lyr.export
            if layer.type == LayerType.LINESTRING:
                if layer.properties.get("comboBox_ObjectType") == "Thick Line" and wl:
                    files.append({"dirs": ["web/js/lib/meshline"]})
                    wl = False

            elif layer.type == LayerType.POINTCLOUD and pc:
                files.append({"dirs": ["web/js/lib/potree-core"], "subdirs": True})
                files.append({"files": ["web/js/pointcloudlayer.js"]})
                pc = False

        # model loades and model files
        for manager in self.modelManagers:
            for f in manager.filesToCopy():
                if f not in files:
                    files.append(f)

        # animation
        if self.settings.isAnimationEnabled():
            files.append({"dirs": ["web/js/lib/tweenjs"]})

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
    """Base class for exporters that used by Processing algorithms."""

    def __init__(self, settings=None):
        self.isWebEngine = (webview.currentWebViewType == webview.WEBVIEWTYPE_WEBENGINE)

        self.settings = settings or ExportSettings()
        self.settings.isPreview = True
        self.settings.requiresJsonSerializable = self.isWebEngine

        if self.isWebEngine:
            self.view = webview.Q3DView()
            self.page = webview.Q3DWebPage(self.view)
            self.view.setPage(self.page)
            self.view.show()
        else:
            self.page = webview.Q3DWebPage()

        self.iface = Q3DInterface(self.settings, self.page)
        self.iface.statusMessage.connect(self.iface.showStatusMessage)

        self.controller = Q3DController(self.settings)
        self.controller.setupConnections(self.iface)

    def loadSettings(self, filename=None):
        self.settings.loadSettingsFromFile(filename)

    def setMapSettings(self, settings):
        self.settings.setMapSettings(settings)

    def initWebPage(self, width, height):
        logger.info(f"The view size is set to {width}x{height} px.")

        loop = QEventLoop()
        self.page.ready.connect(loop.quit)

        if self.isWebEngine:
            self.view.setFixedSize(width, height)
            url = self.page.url()

        else:
            self.page.setViewportSize(QSize(width, height))
            url = self.page.mainFrame().url()

        if url.isEmpty():
            self.page.setup(self.settings)
        else:
            self.page.reload()

        loop.exec()

        self.page.ready.disconnect(loop.quit)

    def mkdir(self, filename):
        dir = QFileInfo(filename).dir()
        if not dir.exists():
            QDir().mkpath(dir.absolutePath())


class ImageExporter(BridgeExporterBase):
    """Exporter class for generating static image outputs of 3D scenes.

    This exporter is used by a Processing algorithm.
    """

    def render(self, cameraState=None, cancelSignal=None):
        if self.page is None:
            return QImage(), "Page not ready"

        # set camera position and camera target
        if cameraState:
            self.page.setCameraState(cameraState)

        # build scene
        self.controller.buildScene(update_extent=False)

        err = self.page.waitForSceneLoaded(cancelSignal)

        # header and footer labels
        self.page.runScript('setHFLabel(pyData())', data=self.settings.widgetProperties("Label"))

        if self.isWebEngine:
            size = self.view.size()
        else:
            size = self.page.viewportSize()

        logger.info("Rendering scene.")

        image = QImage(size.width(), size.height(), QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(image)

        if self.isWebEngine:
            self.page.requestRendering(waitUntilFinished=True)
            self.view.render(painter)
        else:
            self.page.runScript("app.render()")
            self.page.mainFrame().render(painter)

        painter.end()
        return image, err

    def export(self, filename, cameraState=None, cancelSignal=None):
        # prepare output directory
        self.mkdir(filename)

        image, err = self.render(cameraState, cancelSignal)
        image.save(filename)
        logger.info(f"Image saved to {filename}.")

        return err


class ModelExporter(BridgeExporterBase):
    """Exporter class for generating 3D model files in glTF format.

    This exporter is used by a Processing algorithm.
    """

    def __init__(self, settings=None):
        super().__init__(settings)
        self.settings.requiresJsonSerializable = True

    def initWebPage(self, width, height):
        super().initWebPage(width, height)
        self.page.loadScriptFile(ScriptFile.GLTFEXPORTER)

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
