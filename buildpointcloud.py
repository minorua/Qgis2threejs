# -*- coding: utf-8 -*-
"""
/***************************************************************************
 buildpointcloud.py

 begin     : 2020-05-15
 copyright : (C) 2020 Minoru Akagi
 email     : akaginch@gmail.com
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
from .conf import DEBUG_MODE
from .buildlayer import LayerBuilder


class PointCloudLayerBuilder(LayerBuilder):

    def __init__(self, settings, layer, pathRoot=None, urlRoot=None, progress=None):
        """if both pathRoot and urlRoot are None, object is built in all_in_dict mode."""
        LayerBuilder.__init__(self, settings, None, layer, pathRoot, urlRoot, progress)

    def build(self):
        d = {
            "type": "layer",
            "id": self.layer.jsLayerId,
            "properties": self.layerProperties()
        }

        if DEBUG_MODE:
            d["PROPERTIES"] = self.properties

        return d

    def layerProperties(self):
        p = LayerBuilder.layerProperties(self)
        p["type"] = "pc"
        p["url"] = self.properties.get("url")
        p["opacity"] = self.properties.get("spinBox_Opacity", 100) / 100
        return p

    def blocks(self):
        return []
