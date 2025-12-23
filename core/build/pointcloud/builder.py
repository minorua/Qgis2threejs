# -*- coding: utf-8 -*-
# (C) 2020 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2020-05-15

from ..layerbuilderbase import LayerBuilderBase
from ....conf import DEBUG_MODE
from ....utils import int_color


class PointCloudLayerBuilder(LayerBuilderBase):
    """Builder for point cloud layers (currently limited to Potree format).

    This builder creates a simple layer object that references an
    externally hosted Potree dataset. It does not copy the large
    point cloud files into the export.
    """

    def __init__(self, settings, layer, progress=None, log=None, isInUiThread=True):
        """See `LayerBuilderBase.__init__()` for argument details."""
        super().__init__(settings, layer, progress=progress, log=log, isInUiThread=isInUiThread)

    def build(self, build_blocks=False, abortSignal=None):
        """Generate the export data structure for the point cloud."""
        d = {
            "type": "layer",
            "id": self.layer.jsLayerId,
            "properties": self.layerProperties()
        }

        if not self.settings.isPreview:
            url = d["properties"]["url"]
            self.log("URL: {}".format(url))
            if url.startswith("file:"):
                filename = url.split("/")[-1]
                self.log("""
Point cloud data files in Potree format will not be copied to the output data directory.
You need to upload them to a web server and replace the {0} file URL in the scene.js{1}
with valid one that points to the {0} file on the web server.""".format(filename, "" if self.settings.localMode else "on"), warning=True)

        if DEBUG_MODE:
            d["PROPERTIES"] = self.properties

        return d

    def layerProperties(self):
        p = LayerBuilderBase.layerProperties(self)
        p["type"] = "pc"
        p["url"] = self.properties.get("url")
        p["opacity"] = self.properties.get("spinBox_Opacity", 100) / 100
        p["colorType"] = self.properties.get("comboBox_ColorType", "RGB")
        if p["colorType"] == "COLOR":
            p["color"] = int_color(self.properties.get("colorButton_Color"))
        p["boxVisible"] = self.properties.get("checkBox_BoxVisible", False)
        return p

    def subBuilders(self):
        return []
