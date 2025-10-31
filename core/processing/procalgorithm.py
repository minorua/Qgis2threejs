# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-06

import os
import qgis
from qgis.PyQt.QtCore import QDir, QSize
from qgis.PyQt.QtXml import QDomDocument
from qgis.core import (QgsCoordinateTransform,
                       QgsExpression,
                       QgsGeometry,
                       QgsMemoryProviderUtils,
                       QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterExpression,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterVectorLayer,
                       QgsWkbTypes)

from ..export.export import ThreeJSExporter, ImageExporter, ModelExporter
from ..exportsettings import ExportSettings
from ..mapextent import MapExtent
from ...conf import DEBUG_MODE, DEF_SETS, P_OPEN_DIRECTORY
from ...utils import logger, openDirectory


class AlgorithmBase(QgsProcessingAlgorithm):

    INPUT = "INPUT"
    SCALE = "SCALE"
    BUFFER = "BUFFER"
    TEX_WIDTH = "TEX_WIDTH"
    TEX_HEIGHT = "TEX_HEIGHT"
    TITLE_FIELD = "TITLE"
    CF_FILTER = "CF_FILTER"
    SETTINGS = "SETTINGS"
    HEADER = "HEADER"
    FOOTER = "FOOTER"
    OUTPUT = "OUTPUT"

    def __init__(self):
        super().__init__()

        self.settings = ExportSettings()

    def createInstance(self):
        logger.debug("createInstance(): %s", self.__class__.__name__)
        return self.__class__()

    def flags(self):
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    # def tags(self):
    #  return []

    def tr(self, string):
        return string
        # return QCoreApplication.translate("Qgis2threejsAlg", string)

    def addAdvancedParameter(self, param):
        param.setFlags(param.flags() | param.FlagAdvanced)
        self.addParameter(param)

    def initAlgorithm(self, configuration={}, label=True):
        logger.debug("initAlgorithm(): %s", self.__class__.__name__)

        qgis_iface = qgis.utils.plugins["Qgis2threejs"].iface
        self.settings.loadSettingsFromFile()
        self.settings.setMapSettings(qgis_iface.mapCanvas().mapSettings())

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT,
                self.tr("Output Directory")
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.INPUT,
                self.tr("Coverage Layer"),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.TITLE_FIELD,
                self.tr("Title Field"),
                None,
                self.INPUT,
                QgsProcessingParameterField.Any
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.CF_FILTER,
                self.tr("Current Feature Filter")
            )
        )

        enum = ["Fit to Geometry", "Fixed Scale (based on map canvas)"]
        self.addAdvancedParameter(
            QgsProcessingParameterEnum(
                self.SCALE,
                self.tr("Scale Mode"),
                enum,
                defaultValue=enum[0]
            )
        )

        self.addAdvancedParameter(
            QgsProcessingParameterNumber(
                self.BUFFER,
                self.tr("Buffer (%)"),
                defaultValue=10
            )
        )

        self.addAdvancedParameter(
            QgsProcessingParameterNumber(
                self.TEX_WIDTH,
                self.tr("Texture base width (px)"),
                defaultValue=DEF_SETS.TEXTURE_SIZE
            )
        )

        self.addAdvancedParameter(
            QgsProcessingParameterNumber(
                self.TEX_HEIGHT,
                self.tr('Texture base height (px)\n'
                        '    Leave this zero to respect aspect ratio of buffered geometry bounding box (in "Fit to Geometry" scale mode)\n'
                        '    or map canvas (in "Fixed scale" scale mode).'),
                defaultValue=0
                # ,optional=True
            )
        )

        if label:
            self.addAdvancedParameter(
                QgsProcessingParameterExpression(
                    self.HEADER,
                    self.tr("Header Label"),
                    "'{}'".format(self.settings.headerLabel().replace("'", "''")),
                    self.INPUT
                )
            )

            self.addAdvancedParameter(
                QgsProcessingParameterExpression(
                    self.FOOTER,
                    self.tr("Footer Label"),
                    "'{}'".format(self.settings.footerLabel().replace("'", "''")),
                    self.INPUT
                )
            )

        self.addAdvancedParameter(
            QgsProcessingParameterFile(self.SETTINGS,
                                       self.tr('Export Settings File (.qto3settings)'),
                                       extension="qto3settings",
                                       optional=True
                                       )
        )

    def prepareAlgorithm(self, parameters, context, feedback):
        clayer = self.parameterAsLayer(parameters, self.INPUT, context)
        cf_filter = self.parameterAsBool(parameters, self.CF_FILTER, context)
        settings_path = self.parameterAsString(parameters, self.SETTINGS, context)

        self.transform = QgsCoordinateTransform(clayer.crs(),
                                                context.project().crs(),
                                                context.project())

        self.settings.loadSettingsFromFile(settings_path or None)

        if cf_filter and clayer not in self.settings.mapSettings.layers():
            msg = self.tr('Coverage layer must be visible when "Current Feature Filter" option is checked.')
            feedback.reportError(msg, True)
            return False
        return True

    def processAlgorithm(self, parameters, context, feedback):
        logger.debug("processAlgorithm(): %s", self.__class__.__name__)

        clayer = self.parameterAsLayer(parameters, self.INPUT, context)
        title_field = self.parameterAsString(parameters, self.TITLE_FIELD, context)
        cf_filter = self.parameterAsBool(parameters, self.CF_FILTER, context)
        fixed_scale = self.parameterAsEnum(parameters, self.SCALE, context)   # == 1
        buf = self.parameterAsDouble(parameters, self.BUFFER, context)
        tex_width = self.parameterAsInt(parameters, self.TEX_WIDTH, context)
        orig_tex_height = self.parameterAsInt(parameters, self.TEX_HEIGHT, context)

        header_exp = QgsExpression(self.parameterAsExpression(parameters, self.HEADER, context))
        footer_exp = QgsExpression(self.parameterAsExpression(parameters, self.FOOTER, context))

        exp_context = clayer.createExpressionContext()

        out_dir = self.parameterAsString(parameters, self.OUTPUT, context)
        if not QDir(out_dir).exists():
            QDir().mkpath(out_dir)

        if DEBUG_MODE:
            openDirectory(out_dir)

        mapSettings = self.settings.mapSettings
        be = self.settings.baseExtent()
        rotation = be.rotation()
        orig_size = mapSettings.outputSize()

        if cf_filter:
            cf_layer = QgsMemoryProviderUtils.createMemoryLayer("current feature",
                                                                clayer.fields(),
                                                                clayer.wkbType(),
                                                                clayer.crs())
            layers = [cf_layer if lyr == clayer else lyr for lyr in mapSettings.layers()]
            mapSettings.setLayers(layers)

            doc = QDomDocument("qgis")
            clayer.exportNamedStyle(doc)
            cf_layer.importNamedStyle(doc)

        total = clayer.featureCount()
        for current, feature in enumerate(clayer.getFeatures()):
            if feedback.isCanceled():
                break

            if cf_filter:
                cf_layer.startEditing()
                cf_layer.deleteFeatures([f.id() for f in cf_layer.getFeatures()])
                cf_layer.addFeature(feature)
                cf_layer.commitChanges()

            title = feature.attribute(title_field)
            feedback.setProgressText("({}/{}) Exporting {}...".format(current + 1, total, title))
            logger.info("Exporting {}...".format(title))

            # extent
            geometry = QgsGeometry(feature.geometry())
            geometry.transform(self.transform)
            center = geometry.centroid().asPoint()

            if fixed_scale or geometry.type() == QgsWkbTypes.PointGeometry:
                tex_height = orig_tex_height or int(tex_width * orig_size.height() / orig_size.width())
                extent = MapExtent(center, be.width(), be.width() * tex_height / tex_width, rotation).scale(1 + buf / 100)
            else:
                geometry.rotate(rotation, center)
                rect = geometry.boundingBox().scaled(1 + buf / 100)
                center = MapExtent.rotateQgsPoint(rect.center(), rotation, center)
                if orig_tex_height:
                    tex_height = orig_tex_height
                    tex_ratio = tex_width / tex_height
                    rect_ratio = rect.width() / rect.height()
                    if tex_ratio > rect_ratio:
                        extent = MapExtent(center, rect.height() * tex_ratio, rect.height(), rotation)
                    else:
                        extent = MapExtent(center, rect.width(), rect.width() / tex_ratio, rotation)
                else:
                    # fit to buffered geometry bounding box
                    extent = MapExtent(center, rect.width(), rect.height(), rotation)
                    tex_height = tex_width * rect.height() / rect.width()

            extent.toMapSettings(mapSettings)
            mapSettings.setOutputSize(QSize(tex_width, tex_height))

            self.settings.setMapSettings(mapSettings)

            # labels
            exp_context.setFeature(feature)
            self.settings.setHeaderLabel(header_exp.evaluate(exp_context))
            self.settings.setFooterLabel(footer_exp.evaluate(exp_context))

            self.export(title, out_dir, feedback)

            feedback.setProgress(int(current / total * 100))

        if P_OPEN_DIRECTORY and not DEBUG_MODE:
            openDirectory(out_dir)

        return {}

    def export(self, title):
        pass


class ExportAlgorithm(AlgorithmBase):

    TEMPLATE = "TEMPLATE"

    def initAlgorithm(self, config):
        super().initAlgorithm(config)

        templates = ["3DViewer.html", "3DViewer(dat-gui).html", "Mobile.html"]
        self.addParameter(
            QgsProcessingParameterEnum(
                self.TEMPLATE,
                self.tr("Template"),
                templates
            )
        )

    def name(self):
        return 'exportweb'

    def displayName(self):
        return self.tr("Export as Web Page")

    def prepareAlgorithm(self, parameters, context, feedback):
        super().prepareAlgorithm(parameters, context, feedback)
        self.exporter = ThreeJSExporter(self.settings)
        return True

    def export(self, title, out_dir, feedback):
        # scene title
        filename = "{}.html".format(title)
        filepath = os.path.join(out_dir, filename)
        self.settings.setOutputFilename(filepath)

        err_msg = self.settings.checkValidity()
        if err_msg:
            feedback.reportError("Invalid settings: " + err_msg)
            return False

        # export
        err = self.exporter.export(cancelSignal=feedback.canceled)
        return True


class ExportImageAlgorithm(AlgorithmBase):

    WIDTH = "WIDTH"
    HEIGHT = "HEIGHT"

    def initAlgorithm(self, config):
        super().initAlgorithm(config)

        self.addParameter(
            QgsProcessingParameterNumber(
                self.WIDTH,
                self.tr("Image Width"),
                defaultValue=2480,
                minValue=1)
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.HEIGHT,
                self.tr("Image Height"),
                defaultValue=1748,
                minValue=1)
        )

    def name(self):
        return 'exportimage'

    def displayName(self):
        return self.tr("Export as Image")

    def prepareAlgorithm(self, parameters, context, feedback):
        if not super().prepareAlgorithm(parameters, context, feedback):
            return False

        width = self.parameterAsInt(parameters, self.WIDTH, context)
        height = self.parameterAsInt(parameters, self.HEIGHT, context)

        feedback.setProgressText("Preparing a web page for off-screen rendering...")

        self.exporter = ImageExporter(self.settings)
        self.exporter.initWebPage(width, height)
        return True

    def export(self, title, out_dir, feedback):
        # image path
        filename = "{}.png".format(title)
        filepath = os.path.join(out_dir, filename)

        err_msg = self.settings.checkValidity()
        if err_msg:
            feedback.reportError("Invalid settings: " + err_msg)
            return False

        # export
        err = self.exporter.export(filepath, cancelSignal=feedback.canceled)

        return True


class ExportModelAlgorithm(AlgorithmBase):

    def initAlgorithm(self, config):
        super().initAlgorithm(config, label=False)

    def name(self):
        return 'exportmodel'

    def displayName(self):
        return self.tr("Export as 3D Model")

    def prepareAlgorithm(self, parameters, context, feedback):
        if not super().prepareAlgorithm(parameters, context, feedback):
            return False

        self.modelType = "gltf"

        feedback.setProgressText("Preparing a web page for 3D model export...")

        self.exporter = ModelExporter(self.settings)
        self.exporter.initWebPage(500, 500)
        return True

    def export(self, title, out_dir, feedback):
        # model path
        filename = "{}.{}".format(title, self.modelType)
        filepath = os.path.join(out_dir, filename)

        err_msg = self.settings.checkValidity()
        if err_msg:
            feedback.reportError("Invalid settings: " + err_msg)
            return False

        # export
        err = self.exporter.export(filepath, cancelSignal=feedback.canceled)

        return True
