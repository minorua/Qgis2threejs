# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import json
from qgis.PyQt.QtCore import QVariant

from ...const import PropertyID as PID
from ...geometry import VectorGeometry
from ....conf import DEBUG_MODE
from ....utils import logMessage, parseInt


def json_default(o):
    if isinstance(o, QVariant):
        return repr(o)
    raise TypeError(repr(o) + " is not JSON serializable")


class FeatureBlockBuilder:

    def __init__(self, settings, vlayer, jsLayerId, pathRoot=None, urlRoot=None, useZM=VectorGeometry.NotUseZM, z_func=None, grid=None):
        self.settings = settings
        self.vlayer = vlayer
        self.jsLayerId = jsLayerId
        self.pathRoot = pathRoot
        self.urlRoot = urlRoot
        self.useZM = useZM
        self.z_func = z_func
        self.grid = grid

        self.blockIndex = None
        self.startFIdx = None
        self.features = []

    def clone(self):
        return FeatureBlockBuilder(self.settings, self.vlayer, self.jsLayerId,
                                   self.pathRoot, self.urlRoot,
                                   self.useZM, self.z_func, self.grid)

    def setBlockIndex(self, index):
        self.blockIndex = index

    def setFeatures(self, features):
        self.features = features

    def build(self):
        be = self.settings.baseExtent()
        obj_geom_func = self.vlayer.ot.geometry
        mapTo3d = self.settings.mapTo3d()

        feats = []
        for f in self.features:
            d = {}
            d["geom"] = obj_geom_func(f, f.geometry(self.z_func, mapTo3d, self.useZM, be, self.grid))

            if f.material is not None:
                d["mtl"] = f.material
            elif f.model is not None:
                d["model"] = f.model

            if f.attributes is not None:
                d["prop"] = f.attributes

            text = f.prop(PID.LBLTXT)
            if text is not None and text != "":
                d["lbl"] = str(text)
                d["lh"] = f.prop(PID.LBLH)

            if f.hasProp(PID.DLY):
                d["anim"] = {
                    "delay": parseInt(f.prop(PID.DLY)),
                    "duration": parseInt(f.prop(PID.DUR))
                }
                if DEBUG_MODE:
                    logMessage("dly: {}, dur: {}".format(d["anim"]["delay"], d["anim"]["duration"]))

            feats.append(d)

        data = {
            "type": "block",
            "layer": self.jsLayerId,
            "block": self.blockIndex,
            "features": feats,
            "featureCount": len(feats),
            "startIndex": self.startFIdx
        }

        if self.pathRoot is not None:
            with open(self.pathRoot + "{0}.json".format(self.blockIndex), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2 if DEBUG_MODE else None, default=json_default)

            url = self.urlRoot + "{0}.json".format(self.blockIndex)
            return {"url": url, "featureCount": len(feats)}

        else:
            return data
