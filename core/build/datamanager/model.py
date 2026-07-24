# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os

from qgis.PyQt.QtCore import QUrl

from .base import DataManager
from ...const import ScriptFile
from ....utils.js import base64file


class ModelManager(DataManager):

    def __init__(self, exportSettings):
        super().__init__()
        self.exportSettings = exportSettings

    def modelIndex(self, path):
        return self._index(path)

    def build(self, export=True, base64=False):
        a = []
        for path_url in self._list:
            if path_url.startswith("http:") or path_url.startswith("https:"):
                a.append({"url": path_url})

            elif base64:
                _, ext = os.path.splitext(path_url)
                a.append({"base64": base64file(path_url),
                          "ext": ext[1:],
                          "resourcePath": "./data/{}/models/".format(self.exportSettings.outputFileTitle())})
            else:
                if export:
                    url = "./data/{}/models/{}".format(self.exportSettings.outputFileTitle(),
                                                       os.path.basename(path_url))
                else:
                    url = QUrl.fromLocalFile(path_url).toString()

                a.append({"url": url})
        return a

    def hasColladaModel(self):
        for f in self._list:
            _, ext = os.path.splitext(f)
            if ext == ".dae":
                return True
        return False

    def hasGLTFModel(self):
        for f in self._list:
            _, ext = os.path.splitext(f)
            if ext in [".gltf", ".glb"]:
                return True
        return False

    def filesToCopy(self):
        THREE = "web/js/lib/three"
        LOADER = THREE + "/loaders"
        UTILS = THREE + "/utils"

        f = []
        if self._list:
            if self.hasColladaModel():
                f.append({
                    "files": [
                        LOADER + "/ColladaLoader.js",
                        LOADER + "/TGALoader.js"
                    ],
                    "dirs": [
                        LOADER + "/collada"
                    ],
                    "dest": "three/loaders"
                })

            if self.hasGLTFModel():
                f.append({
                    "files": [
                        LOADER + "/GLTFLoader.js"
                    ],
                    "dest": "three/loaders"
                })
                f.append({
                    "files": [
                        UTILS + "/BufferGeometryUtils.js",
                        UTILS + "/SkeletonUtils.js"
                    ],
                    "dest": "three/utils"
                })

            f.append({"files": self._list, "dest": "./data/{}/models".format(self.exportSettings.outputFileTitle())})
        return f

    def moduleFiles(self):
        files = []
        if self._list:
            if self.hasColladaModel():
                files.append(("./three/loaders/ColladaLoader.js", ScriptFile.TYPE_CLASS))

            if self.hasGLTFModel():
                files.append(("./three/loaders/GLTFLoader.js", ScriptFile.TYPE_CLASS))

        return files
