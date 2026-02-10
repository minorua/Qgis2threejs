# -*- coding: utf-8 -*-
# (C) 2021 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2021-11-10

from qgis.PyQt.QtCore import Qt, QSize, QUrl
from qgis.PyQt.QtGui import QCursor, QIcon
from qgis.PyQt.QtWidgets import (QAbstractItemView, QAction, QButtonGroup, QDialog, QInputDialog, QMenu,
                             QMessageBox, QTreeWidget, QTreeWidgetItem, QWidget)
from qgis.core import Qgis, QgsApplication, QgsFieldProxyModel

from .ui.animationpanel import Ui_AnimationPanel
from .ui.keyframedialog import Ui_KeyframeDialog
from ..conf import DEF_SETS, PLUGIN_NAME
from ..core.const import DEMMtlType, LayerType, ATConst
from ..core.exportsettings import Layer
from ..utils import createUid, logger, openHelp, parseInt, pluginDir
from ..utils.gui import selectImageFile


class AnimationPanel(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.isAnimating = False

        self.ui = Ui_AnimationPanel()
        self.ui.setupUi(self)
        self.ui.treeWidgetAnimation = AnimationTreeWidget(self)
        self.ui.treeWidgetAnimation.setObjectName("treeWidgetAnimation")
        self.ui.verticalLayout.addWidget(self.ui.treeWidgetAnimation)

        self.tree = self.ui.treeWidgetAnimation

        self.iconPlay = QIcon(pluginDir("svg", "play.svg"))    # QgsApplication.getThemeIcon("temporal_navigation/forward.svg")
        self.iconStop = QIcon(pluginDir("svg", "stop.svg"))    # QgsApplication.getThemeIcon("temporal_navigation/stop.svg")
        self.iconNarration = QgsApplication.getThemeIcon("mIconInfo.svg")
        self.iconEasing = {}

    def setup(self, wnd, settings):
        self.wnd = wnd
        self.webPage = wnd.webPage
        self.controller = wnd.controller

        self.ui.toolButtonAdd.setIcon(QgsApplication.getThemeIcon("symbologyAdd.svg"))
        self.ui.toolButtonEdit.setIcon(QgsApplication.getThemeIcon("symbologyEdit.svg"))
        self.ui.toolButtonRemove.setIcon(QgsApplication.getThemeIcon("symbologyRemove.svg"))
        self.ui.toolButtonPlay.setIcon(self.iconPlay)

        self.ui.toolButtonAdd.clicked.connect(self.tree.addNewItem)
        self.ui.toolButtonEdit.clicked.connect(self.tree.onItemEdit)
        self.ui.toolButtonRemove.clicked.connect(self.tree.removeSelectedItems)
        self.ui.toolButtonPlay.clicked.connect(self.playButtonClicked)

        self.tree.setup(wnd, settings)

        self.setData(settings.animationData())

        if self.webPage:
            self.tree.currentItemChanged.connect(self.currentItemChanged)
            self.currentItemChanged(None, None)

            self.webPage.bridge.animationStopped.connect(self.animationStopped)
        else:
            self.setEnabled(False)      # animation panel gets disabled when exporter has no preview.

    def teardown(self):
        self.wnd = None
        self.webPage = None
        self.controller = None
        self.tree.teardown()

    def data(self):
        d = self.tree.data()
        d["repeat"] = self.ui.checkBoxLoop.isChecked()
        return d

    def setData(self, data):
        self.ui.checkBoxLoop.setChecked(data.get("repeat", False))
        self.tree.setData(data)

    def playButtonClicked(self, _):
        if self.isAnimating:
            self.stopAnimation()
        else:
            self.playAnimation(repeat=self.ui.checkBoxLoop.isChecked())

    def playAnimation(self, items=None, repeat=False):
        self.wnd.settings.setAnimationData(self.data())

        self._warnings = []

        dataList = []
        if items is None:
            for track in self.wnd.settings.enabledValidTracks(warning_log=self._log):
                layerId = track.get("layerId")
                if layerId is None:
                    dataList.append(track)
                else:
                    layer = self.wnd.settings.getLayerByJSLayerId(layerId)
                    if layer:
                        t = track.get("type")
                        if t in (ATConst.ITEM_TRK_TEXTURE, ATConst.ITEM_TRK_GROWING_LINE):
                            self._updateLayer(layer, t)

                        dataList.append(track)
        else:
            for item in items:
                t = item.type()
                if t in (ATConst.ITEM_TRK_TEXTURE, ATConst.ITEM_TRK_GROWING_LINE):
                    mapLayerId = item.parent().data(0, ATConst.DATA_LAYER_ID)
                elif t in (ATConst.ITEM_TEXTURE, ATConst.ITEM_GROWING_LINE):
                    mapLayerId = item.parent().parent().data(0, ATConst.DATA_LAYER_ID)
                else:
                    mapLayerId = None

                if mapLayerId:
                    layer = self.wnd.settings.getLayer(mapLayerId)
                    self._updateLayer(layer, t)

                data = self.tree.transitionData(item, exclude_narration=bool(t & ATConst.ITEM_MBR))
                if data:
                    dataList.append(data)

        msg = ""
        timeout_ms = 5000
        if self._warnings:
            msg = "Animation warning{}:<br><ul>".format("s" if len(self._warnings) > 1 else "")
            for w in self._warnings:
                msg += "<li>" + w + "</li>"
            msg += "</ul>"
            timeout_ms = 0

        if len(dataList):
            self.isAnimating = True
            self.controller.taskManager.addSendDataTask({
                "type": "animation",
                "tracks": dataList,
                "repeat": repeat
            })

            self.ui.toolButtonPlay.setIcon(self.iconStop)
            self.ui.checkBoxLoop.setEnabled(False)
        else:
            if not msg:
                msg = "Animation: "
            msg += "There are no tracks to play."

            self.ui.toolButtonPlay.setChecked(False)

        if msg:
            self.webPage.showMessageBar(msg, timeout_ms, warning=True)

    def _updateLayer(self, layer, trackType):
        if trackType in (ATConst.ITEM_TRK_TEXTURE, ATConst.ITEM_TEXTURE):
            layer = layer.clone()
            layer.opt.onlyMaterial = True
            layer.opt.allMaterials = True

        tm = self.controller.taskManager
        tm.addRunScriptTask("preview.renderEnabled = false;")
        tm.addBuildLayerTask(layer)
        tm.addRunScriptTask("preview.renderEnabled = true;")

    def _log(self, msg):
        self._warnings.append(msg)
        logger.info("Animation: " + msg)

    def stopAnimation(self):
        self.webPage.runScript("stopAnimation()")

    # @pyqtSlot()
    def animationStopped(self):
        self.ui.toolButtonPlay.setIcon(self.iconPlay)
        self.ui.toolButtonPlay.setChecked(False)
        self.ui.checkBoxLoop.setEnabled(True)
        self.isAnimating = False

    def updateKeyframeView(self):
        view = self.controller.cameraState(flat=True)

        msg = "Are you sure you want to update the camera position and focal point of this keyframe?"
        if QMessageBox.question(self, PLUGIN_NAME, msg) == QMessageBox.StandardButton.Yes:
            item = self.tree.currentItem()
            item.setData(0, ATConst.DATA_CAMERA, view)

    def currentItemChanged(self, current, previous):
        self.ui.toolButtonAdd.setEnabled(bool(current))

        b = bool(current and not (current.type() & ATConst.ITEM_TOPLEVEL))
        self.ui.toolButtonEdit.setEnabled(b)
        self.ui.toolButtonRemove.setEnabled(b)

    def showNarrativeBox(self, content):
        self.controller.sendData({"type": "narration",
                                  "content": content})


class AnimationTreeWidget(QTreeWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.panel = parent
        self.dialog = None

        root = self.invisibleRootItem()
        root.setFlags(root.flags() & ~Qt.ItemFlag.ItemIsDropEnabled)

        self.header().setVisible(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setExpandsOnDoubleClick(False)

    def setup(self, wnd, settings):
        self.wnd = wnd
        self.webPage = wnd.webPage
        self.controller = wnd.controller

        self.settings = settings

        self.icons = wnd.icons
        self.cameraIcon = QgsApplication.getThemeIcon("mIconCamera.svg") if Qgis.QGIS_VERSION_INT >= 31600 else QIcon(pluginDir("svg", "camera.svg"))
        self.keyframeIcon = QIcon(pluginDir("svg", "keyframe.svg"))
        self.effectIcon = QgsApplication.getThemeIcon("mLayoutItemPolyline.svg")

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)
        self.currentItemChanged.connect(self.currentTreeItemChanged)
        self.itemDoubleClicked.connect(self.onItemDoubleClicked)

        # context menu
        self.actionAdd = QAction("Add", self)           # NOTE: may be hidden
        self.actionAdd.triggered.connect(self.addNewItem)

        self.actionRemove = QAction("Remove...", self)
        self.actionRemove.triggered.connect(self.removeSelectedItems)

        self.actionEdit = QAction("Edit...", self)
        self.actionEdit.triggered.connect(self.onItemEdit)

        self.actionRename = QAction("Rename...", self)
        self.actionRename.triggered.connect(self.renameTrack)

        self.actionPlay = QAction("Play", self)
        self.actionPlay.triggered.connect(self.playAnimation)

        self.actionShowNarBox = QAction("Preview narrative content", self)
        self.actionShowNarBox.triggered.connect(self.showNarrativeBox)

        self.actionUpdateView = QAction("Set current view to this keyframe...", self)
        self.actionUpdateView.triggered.connect(self.panel.updateKeyframeView)

        self.actionOpacity = QAction("Change opacity...", self)
        self.actionOpacity.triggered.connect(self.addOpacityItem)

        self.actionTexture = QAction("Change texture...", self)
        self.actionTexture.triggered.connect(self.addTextureItem)

        self.actionGrowLine = QAction("Growing line...", self)
        self.actionGrowLine.triggered.connect(self.addGrowLineItem)

        self.actionProperties = QAction("Properties...", self)
        self.actionProperties.triggered.connect(self.showDialog)

        self.ctxMenuTrack = QMenu(self)
        self.ctxMenuTrack.addAction(self.actionPlay)
        self.ctxMenuTrack.addAction(self.actionRename)
        self.ctxMenuTrack.addSeparator()
        self.ctxMenuTrack.addAction(self.actionAdd)
        self.ctxMenuTrack.addAction(self.actionEdit)
        self.ctxMenuTrack.addSeparator()
        self.ctxMenuTrack.addAction(self.actionRemove)

        self.ctxMenuKeyframe = QMenu(self)
        self.ctxMenuKeyframe.addAction(self.actionShowNarBox)
        self.ctxMenuKeyframe.addAction(self.actionPlay)
        self.ctxMenuKeyframe.addSeparator()
        self.ctxMenuKeyframe.addAction(self.actionEdit)
        self.ctxMenuKeyframe.addAction(self.actionUpdateView)
        self.ctxMenuKeyframe.addSeparator()
        self.ctxMenuKeyframe.addAction(self.actionRemove)

        self.ctxMenuLayerAdd = QMenu(self)
        self.ctxMenuLayerAdd.addActions([self.actionOpacity, self.actionTexture, self.actionGrowLine])

        self.ctxMenuLayer = QMenu(self)
        self.ctxMenuLayer.addMenu("Add").addActions(self.ctxMenuLayerAdd.actions())
        self.ctxMenuLayer.addSeparator()
        self.ctxMenuLayer.addAction(self.actionProperties)

    def teardown(self):
        self.panel = None
        self.wnd = None
        self.webPage = None
        self.controller = None

    def dropEvent(self, event):
        items = self.selectedItems()
        p = items[0].parent()
        dp = False
        for item in items[1:]:
            if item.parent() != p:
                dp = True

        item = items[0]
        dest = self.itemAt(event.pos())
        accept = False
        if dest and item.type() & ATConst.ITEM_MBR and not dp:
            if item.type() == dest.type():
                if item.parent().parent() == item.parent().parent():
                    accept = True
            elif item.parent().type() == dest.type():
                if item.parent().parent() == dest.parent():
                    accept = True

        if item.type() == ATConst.ITEM_GROWING_LINE:
            accept = False

        if not accept:
            event.setDropAction(Qt.DropAction.IgnoreAction)
            self.wnd.ui.statusbar.showMessage("Cannot move item(s) there.", 3000)

        return QTreeWidget.dropEvent(self, event)

    def initTree(self):
        self.clear()

    def addLayer(self, id_layer):
        if isinstance(id_layer, Layer):
            layer = id_layer
            layerId = id_layer.layerId
        else:
            layerId = id_layer
            layer = self.settings.getLayer(layerId)
            if not layer:
                return

        item = QTreeWidgetItem(self, [layer.name], ATConst.ITEM_TL_LAYER)
        item.setData(0, ATConst.DATA_LAYER_ID, layerId)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setIcon(0, self.icons[layer.type])
        item.setExpanded(True)

        return item

    def currentLayer(self):
        item = self.currentItem()
        if item:
            while item.parent():
                item = item.parent()

            return self.getLayerFromLayerItem(item)

    def getLayerFromLayerItem(self, item):
        layerId = item.data(0, ATConst.DATA_LAYER_ID)
        return self.settings.getLayer(layerId)

    def findLayerItem(self, layerId):
        root = self.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.type() == ATConst.ITEM_TL_LAYER and item.data(0, ATConst.DATA_LAYER_ID) == layerId:
                return item

    def setLayerHidden(self, layerId, b=True):
        item = self.findLayerItem(layerId)
        if item:
            item.setHidden(b)

    def addNewItem(self):
        item = self.currentItem()
        if item is None:
            return

        typ = item.type()
        parent = None
        if typ & ATConst.ITEM_TOPLEVEL:
            if typ == ATConst.ITEM_TL_CAMERA:
                parent = self.addTrackItem(item, ATConst.ITEM_TRK_CAMERA)
                child = self.addKeyframeItem(parent)
                self.setCurrentItem(child)
                self.wnd.ui.statusbar.showMessage("A new track and a keyframe have been added.", 5000)
            else:
                layer = self.getLayerFromLayerItem(item)
                self.actionTexture.setVisible(layer.type == LayerType.DEM)
                self.actionGrowLine.setVisible(layer.type == LayerType.LINESTRING)
                self.ctxMenuLayerAdd.popup(QCursor.pos())
            return

        trk_type = typ if typ & ATConst.ITEM_TRK else typ - ATConst.ITEM_MBR + ATConst.ITEM_TRK
        if trk_type == ATConst.ITEM_TRK_CAMERA:
            added = self.addKeyframeItem()
            self.setCurrentItem(added)

        elif trk_type == ATConst.ITEM_TRK_OPACITY:
            self.addOpacityItem()

        elif trk_type == ATConst.ITEM_TRK_TEXTURE:
            self.addTextureItem()

        elif trk_type == ATConst.ITEM_TRK_GROWING_LINE:
            if typ == ATConst.ITEM_TRK_GROWING_LINE and item.childCount() == 0:
                self.addGrowLineItem()
            else:
                QMessageBox.warning(self, PLUGIN_NAME, "This track can't have more than one item.")

    def removeSelectedItems(self):
        items = self.selectedItems() or [self.currentItem()]
        if len(items) == 0:
            return
        elif len(items) == 1:
            msg = "Are you sure you want to remove '{}'?".format(items[0].text(0))
        else:
            msg = "Are you sure you want to remove {} items?".format(len(items))

        if QMessageBox.question(self, PLUGIN_NAME, msg) != QMessageBox.StandardButton.Yes:
            return

        for item in items:
            item.parent().removeChild(item)

    def uniqueChildName(self, parent, base_name, omit_one=True):
        n = parent.childCount()
        names = [parent.child(i).text(0) for i in range(n)]

        for i in range(n + 1):
            name = base_name
            if i or not omit_one:
                name += " {}".format(i + 1)
            if name not in names:
                return name

    def addTrackItem(self, parent, typ, name=None, enabled=True):

        name = name or self.uniqueChildName(parent, ATConst.defaultName(typ))

        item = QTreeWidgetItem(typ)
        item.setText(0, name)
        item.setFlags(Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)

        parent.addChild(item)
        item.setExpanded(True)

        return item

    def addKeyframeItem(self, parent=None, keyframe=None):
        if parent is None:
            item = self.currentItem()
            if not item:
                return

            t = item.type()
            if t & ATConst.ITEM_MBR:
                parent = item.parent()
                iidx = parent.indexOfChild(item) + 1
            elif t & ATConst.ITEM_TRK:
                parent = item
                iidx = 0
            else:
                return
        else:
            iidx = 0

        keyframe = keyframe or {}
        typ = keyframe.get("type", parent.type() - ATConst.ITEM_TRK + ATConst.ITEM_MBR)
        name = keyframe.get("name") or self.uniqueChildName(parent, "keyframe", omit_one=False)

        item = QTreeWidgetItem(typ)
        item.setText(0, name)

        item.setData(0, ATConst.DATA_EASING, keyframe.get("easing", ATConst.EASING_LINEAR))
        item.setData(0, ATConst.DATA_DURATION, keyframe.get("duration", DEF_SETS.ANM_DURATION))
        item.setData(0, ATConst.DATA_DELAY, keyframe.get("delay", 0))

        icon = None
        if typ == ATConst.ITEM_CAMERA:
            item.setData(0, ATConst.DATA_CAMERA, keyframe.get("camera") or self.controller.cameraState(flat=True))

        elif typ == ATConst.ITEM_OPACITY:
            item.setData(0, ATConst.DATA_OPACITY, keyframe.get("opacity", 1))

        elif typ == ATConst.ITEM_TEXTURE:
            item.setData(0, ATConst.DATA_MTL_ID, keyframe.get("mtlId", ""))
            item.setData(0, ATConst.DATA_EFFECT, keyframe.get("effect", 0))

        elif typ == ATConst.ITEM_GROWING_LINE:
            item.setData(0, ATConst.DATA_SEQ, keyframe.get("sequential", False))
            icon = self.effectIcon

        nar = keyframe.get("narration")
        if nar:
            item.setData(0, ATConst.DATA_NARRATION, {"id": nar["id"], "text": nar["text"]})
            icon = self.panel.iconNarration

        item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsEnabled)
        item.setIcon(0, icon if icon else self.keyframeIcon)

        if iidx:
            parent.insertChild(iidx, item)
        else:
            parent.addChild(item)

        return item

    def keyframe(self, item=None):
        item = item or self.currentItem()
        if not item or not (item.type() & ATConst.ITEM_MBR):
            return

        typ = item.type()

        k = {
            "type": typ,
            "name": item.text(0)
        }

        easing = item.data(0, ATConst.DATA_EASING)
        if easing:
            k["easing"] = easing

        k["delay"] = item.data(0, ATConst.DATA_DELAY)
        k["duration"] = item.data(0, ATConst.DATA_DURATION)

        n = item.data(0, ATConst.DATA_NARRATION)
        if n:
            k["narration"] = n

        if typ == ATConst.ITEM_CAMERA:
            k["camera"] = item.data(0, ATConst.DATA_CAMERA)

        elif typ == ATConst.ITEM_OPACITY:
            k["opacity"] = item.data(0, ATConst.DATA_OPACITY)

        elif typ == ATConst.ITEM_TEXTURE:
            layer = self.getLayerFromLayerItem(item.parent().parent())
            if layer:
                id = item.data(0, ATConst.DATA_MTL_ID)
                k["mtlId"] = id
                k["mtlIndex"] = layer.mtlIndex(id)
                k["effect"] = item.data(0, ATConst.DATA_EFFECT)

        elif typ == ATConst.ITEM_GROWING_LINE:
            k["sequential"] = item.data(0, ATConst.DATA_SEQ)

        return k

    def trackData(self, item):
        if not item:
            return {}

        typ = item.type()
        if typ & ATConst.ITEM_TRK:
            track = item
        elif typ & ATConst.ITEM_MBR:
            track = item.parent()
        else:
            return {}

        items = [track.child(i) for i in range(track.childCount())]

        d = {
            "type": track.type(),
            "name": track.text(0),
            "enabled": bool(track.checkState(0)),
            "keyframes": [self.keyframe(item) for item in items]
        }

        if track.parent().type() == ATConst.ITEM_TL_LAYER:
            layer = self.settings.getLayer(track.parent().data(0, ATConst.DATA_LAYER_ID))
            if layer:
                d["layerId"] = layer.jsLayerId
            else:
                logger.error("[Track] Layer not found in export settings.")

        return d

    def _layerData(self, layer=None):
        if not layer:
            return {}

        layerItem = layer if isinstance(layer, QTreeWidgetItem) else self.findLayerItem(layer)
        if layerItem is None:
            return {}

        items = [layerItem.child(i) for i in range(layerItem.childCount())]

        return {
            "enabled": not layerItem.isDisabled(),
            "tracks": [self.trackData(item) for item in items]
        }

    def _setLayerData(self, layerId, data):
        if layerId is None:
            return

        layerItem = self.findLayerItem(layerId) or self.addLayer(layerId)
        if layerItem is None:
            return

        for _ in range(layerItem.childCount()):
            layerItem.removeChild(layerItem.child(0))

        for track in data.get("tracks", data.get("groups", [])):        # renamed since v2.9
            parent = self.addTrackItem(layerItem, track.get("type"), track.get("name"), track.get("enabled", True))
            for keyframe in track.get("keyframes", []):
                self.addKeyframeItem(parent, keyframe)

    def data(self):
        root = self.invisibleRootItem()
        parent = root.child(0)      # camera motion

        d = {
            "camera": {
                "tracks": [self.trackData(parent.child(i)) for i in range(parent.childCount())]
            }
        }

        layers = {}
        for item in [root.child(i) for i in range(1, root.childCount())]:
            layers[item.data(0, ATConst.DATA_LAYER_ID)] = self._layerData(item)

        if layers:
            d["layers"] = layers

        return d

    def transitionData(self, item=None, exclude_narration=False):
        item = item or self.currentItem()
        if not item:
            return

        typ = item.type()
        if typ & ATConst.ITEM_MBR:
            isKF = (typ != ATConst.ITEM_GROWING_LINE)
            c = 2 if isKF else 1

            p = item.parent()
            iidx = p.indexOfChild(item)

            if isKF and iidx == p.childCount() - 1:
                return

            d = self.trackData(p)
            kfs = d["keyframes"][iidx:iidx + c]
            if exclude_narration:
                kfs[0].pop("narration", None)

            if c == 2:
                kfs[1].pop("narration", None)
            d["keyframes"] = kfs
            return d

        elif typ & ATConst.ITEM_TRK:        # NOTE: exclude_narration is ignored
            return self.trackData(item)

    def setData(self, data):
        self.initTree()

        # camera motion
        item = QTreeWidgetItem(self, ["Camera Motion"], ATConst.ITEM_TL_CAMERA)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setIcon(0, self.cameraIcon)
        item.setExpanded(True)
        self.cameraTLItem = item

        camera = data.get("camera", {})
        for s in camera.get("tracks", camera.get("groups", [])):        # renamed since v2.9
            parent = self.addTrackItem(item, ATConst.ITEM_TRK_CAMERA, s.get("name"), s.get("enabled", True))
            for k in s.get("keyframes", []):
                self.addKeyframeItem(parent, k)

        # layers
        dp = data.get("layers", {})
        for layer in self.settings.layers():
            id = layer.layerId
            self.addLayer(layer)

            d = dp.get(id)
            if d:
                self._setLayerData(id, d)
            self.setLayerHidden(id, not layer.visible)

    def currentItemView(self):
        item = self.currentItem()
        if item and item.type() == ATConst.ITEM_CAMERA:
            return item.data(0, ATConst.DATA_CAMERA)

    def contextMenu(self, pos):
        item = self.itemAt(pos)
        if item is None:
            # blank space
            return

        m = None
        typ = item.type()
        if typ & ATConst.ITEM_TOPLEVEL:
            if typ == ATConst.ITEM_TL_LAYER:
                m = self.ctxMenuLayer

                layer = self.getLayerFromLayerItem(item)
                self.actionTexture.setVisible(layer.type == LayerType.DEM)
                self.actionGrowLine.setVisible(layer.type == LayerType.LINESTRING)
        else:
            if typ & ATConst.ITEM_TRK:
                m = self.ctxMenuTrack
                self.actionAdd.setText("Add" if typ == ATConst.ITEM_TRK_CAMERA else "Add...")
                self.actionAdd.setVisible(bool(typ != ATConst.ITEM_TRK_GROWING_LINE))

            elif typ & ATConst.ITEM_MBR:
                m = self.ctxMenuKeyframe
                self.actionShowNarBox.setVisible(bool(item.data(0, ATConst.DATA_NARRATION)))
                self.actionUpdateView.setVisible(bool(typ == ATConst.ITEM_CAMERA))

        if m:
            m.exec(self.mapToGlobal(pos))

    def currentTreeItemChanged(self, current, previous=None):
        if not current:
            return

        typ = current.type()
        if not (typ & ATConst.ITEM_MBR):
            return

        if typ == ATConst.ITEM_CAMERA:
            # restore the view of current keyframe
            k = self.keyframe()
            if k:
                self.controller.setCameraState(k.get("camera") or {})

        elif typ == ATConst.ITEM_OPACITY:
            layerId = current.parent().parent().data(0, ATConst.DATA_LAYER_ID)
            layer = self.settings.getLayer(layerId)
            if layer:
                opacity = current.data(0, ATConst.DATA_OPACITY)
                self.webPage.runScript("setLayerOpacity({}, {})".format(layer.jsLayerId, opacity))

        elif typ == ATConst.ITEM_TEXTURE:
            layerId = current.parent().parent().data(0, ATConst.DATA_LAYER_ID)
            layer = self.settings.getLayer(layerId)
            if layer:
                layer = layer.clone()
                layer.properties["mtlId"] = current.data(0, ATConst.DATA_MTL_ID)
                layer.opt.onlyMaterial = True
                self.controller.taskManager.addBuildLayerTask(layer)

    def onItemDoubleClicked(self, item=None, column=0):
        item = item or self.currentItem()
        t = item.type()
        if t != ATConst.ITEM_TL_CAMERA:
            self.showDialog(item)

    def onItemEdit(self):
        item = self.currentItem()
        if item:
            t = item.type()
            if t & ATConst.ITEM_MBR:
                self.showDialog(item)
            elif t & ATConst.ITEM_TRK:
                if item.childCount() > 0:
                    self.showDialog(item.child(0))

    def renameTrack(self, item=None):
        item = item or self.currentItem()
        if item:
            name, ok = QInputDialog.getText(self, "Rename track", "Track name", text=item.text(0))
            if ok:
                item.setText(0, name)

    def addOpacityItem(self):
        item = self.currentItem()
        if not item:
            return

        val, ok = QInputDialog.getDouble(self, "Layer Opacity", "Opacity (0 - 1)", 1, 0, 1, 2)
        if ok:
            parent = None
            if item.type() == ATConst.ITEM_TL_LAYER:
                parent = self.addTrackItem(item, ATConst.ITEM_TRK_OPACITY)

            added = self.addKeyframeItem(parent, {
                "type": ATConst.ITEM_OPACITY,
                "name": "opacity '{}'".format(val),
                "opacity": val
            })
            self.setCurrentItem(added)

    def addTextureItem(self):
        item = self.currentItem()
        layer = self.currentLayer()
        if not item or not layer:
            return

        mtlNames = ["[{}] {}".format(i, mtl.get("name", "")) for i, mtl in enumerate(layer.properties.get("materials", [])) if mtl.get("type") != DEMMtlType.COLOR]

        if not mtlNames:
            QMessageBox.warning(self, "Texture", "The layer has no textures.")
            return

        val, ok = QInputDialog.getItem(self, "Texture", "Select a material with texture", mtlNames, 0, False)
        if ok:
            mtlIdx = int(val.split("]")[0][1:])
            mtl = layer.properties["materials"][mtlIdx]

            parent = None
            if item.type() == ATConst.ITEM_TL_LAYER:
                parent = self.addTrackItem(item, ATConst.ITEM_TRK_TEXTURE)

            added = self.addKeyframeItem(parent, {
                "type": ATConst.ITEM_TEXTURE,
                "name": mtl.get("name", "no name"),
                "mtlId": mtl.get("id")
            })
            self.setCurrentItem(added)

    def addGrowLineItem(self):
        item = self.currentItem()
        layer = self.currentLayer()
        if not item or not layer:
            return

        parent = None
        if item.type() == ATConst.ITEM_TL_LAYER:
            parent = self.addTrackItem(item, ATConst.ITEM_TRK_GROWING_LINE)

        added = self.addKeyframeItem(parent, {
            "type": ATConst.ITEM_GROWING_LINE,
            "name": "Growing line"
        })
        self.setCurrentItem(added)

    def showDialog(self, item=None):
        item = item or self.currentItem()
        if item is None:
            return

        t = item.type()
        if t == ATConst.ITEM_TL_LAYER:
            layerId = item.data(0, ATConst.DATA_LAYER_ID)
            layer = self.settings.getLayer(layerId)
            self.wnd.showLayerPropertiesDialog(layer)
            return

        elif t == ATConst.ITEM_TL_CAMERA:
            return

        if t & ATConst.ITEM_TRK:
            item = item.child(0)
            if item is None:
                isKF = (t != ATConst.ITEM_TRK_GROWING_LINE)
                msg = "This track has no items. Please add {}.".format("at least two keyframe items" if isKF else "an item")
                QMessageBox.warning(self, PLUGIN_NAME, msg)
                return

            t = item.type()

        isKF = (t != ATConst.ITEM_GROWING_LINE)
        if isKF:
            if item.parent().childCount() < 2:
                QMessageBox.warning(self, PLUGIN_NAME, "Two or more keyframes are needed for animation to work. Please add a keyframe.")
                return
        else:
            # line growing doesn't work if track item is not checked
            item.parent().setCheckState(0, Qt.CheckState.Checked)

        top_level = item.parent().parent()
        layer = None
        if top_level.type() == ATConst.ITEM_TL_LAYER:
            layerId = top_level.data(0, ATConst.DATA_LAYER_ID)
            layer = self.settings.getLayer(layerId)

        self.panel.setEnabled(False)

        self.dialog = KeyframeDialog(self)
        self.dialog.setup(item, layer)
        self.dialog.finished.connect(self.dialogClosed)
        self.dialog.show()
        self.dialog.exec()

    def dialogClosed(self, result):
        self.panel.setEnabled(True)
        self.dialog = None

    def playAnimation(self):
        item = self.currentItem()
        if item:
            self.panel.playAnimation([item])

    def showNarrativeBox(self):
        item = self.currentItem()
        if item:
            nar = item.data(0, ATConst.DATA_NARRATION)
            if nar:
                self.panel.showNarrativeBox(nar["text"])

    def materialChanged(self, layer):
        layerItem = self.findLayerItem(layer.layerId)
        if not layerItem:
            return

        mtls = {mtl["id"]: mtl for mtl in layer.properties.get("materials", [])}

        for i in range(layerItem.childCount()):
            track = layerItem.child(i)
            if track.type() != ATConst.ITEM_TRK_TEXTURE:
                continue

            for idx in reversed(range(track.childCount())):
                item = track.child(idx)
                mtl = mtls.get(item.data(0, ATConst.DATA_MTL_ID))
                if mtl:
                    item.setText(0, mtl["name"])
                else:
                    logger.info("The material '{}' was removed.".format(item.text(0)))
                    track.removeChild(item)


class KeyframeDialog(QDialog):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.ui = Ui_KeyframeDialog()
        self.ui.setupUi(self)

        self.easingButtons = {
            ATConst.EASING_NONE: self.ui.toolButtonNone,
            ATConst.EASING_LINEAR: self.ui.toolButtonLinear,
            ATConst.EASING_EASE_INOUT: self.ui.toolButtonEaseInOut,
            ATConst.EASING_EASE_IN: self.ui.toolButtonEaseIn,
            ATConst.EASING_EASE_OUT: self.ui.toolButtonEaseOut
        }

        self.ui.buttonGroup = QButtonGroup(self)
        self.ui.buttonGroup.setObjectName("buttonGroup")
        for id, btn in self.easingButtons.items():
            self.ui.buttonGroup.addButton(btn, id)

        self.panel = parent.panel
        self.narId = None
        self.isPlaying = self.isPlayingAll = False

        self.ui.buttonBox.helpRequested.connect(self.helpClicked)

        parent.webPage.bridge.tweenStarted.connect(self.tweenStarted)
        parent.webPage.bridge.animationStopped.connect(self.animationStopped)

    def setup(self, item, layer=None):
        self.type = t = item.type()
        if not self.type & ATConst.ITEM_MBR:
            return

        self.item = item
        self.currentItem = None
        self.isKF = (t != ATConst.ITEM_GROWING_LINE)
        self.layer = layer

        track = item.parent()
        self.kfCount = track.childCount()

        self.setWindowTitle("{} - {}".format(item.parent().text(0), layer.name if layer else "Camera Motion"))

        # set up widgets
        self.ui.toolButtonPlay.setIcon(self.panel.iconPlay)
        self.ui.pushButtonPlayAll.setIcon(self.panel.iconPlay)
        self.ui.toolButtonAddImage.setIcon(QgsApplication.getThemeIcon("mActionAddImage.svg"))
        self.ui.toolButtonPreview.setIcon(self.panel.iconNarration)

        if not self.panel.iconEasing:
            names = {
                ATConst.EASING_LINEAR: "linear",
                ATConst.EASING_EASE_INOUT: "inout",
                ATConst.EASING_EASE_IN: "in",
                ATConst.EASING_EASE_OUT: "out",
                ATConst.EASING_NONE: "none"
            }
            for id, name in names.items():
                self.panel.iconEasing[id] = QIcon(pluginDir("svg", "ease_{}.svg".format(name)))

        size = QSize(25, 18)
        for id, btn in self.easingButtons.items():
            btn.setIconSize(size)
            btn.setIcon(self.panel.iconEasing[id])

        if t == ATConst.ITEM_TEXTURE:
            self.ui.labelComboBox1.setText("Texture")

            for mtl in self.layer.properties.get("materials", []):
                if mtl.get("type") != DEMMtlType.COLOR:
                    name, id = (mtl.get("name", ""), mtl.get("id"))
                    self.ui.comboBox1.addItem(name, id)

            self.ui.labelComboBox2.setText("Effect")
            self.ui.comboBox2.addItem("Fade in", 0)

        elif t == ATConst.ITEM_GROWING_LINE:
            self.ui.labelComboBox1.setText("Animate")

            self.ui.comboBox1.addItem("all lines at once", False)
            self.ui.comboBox1.addItem("each line sequentially", True)
            self.ui.comboBox1.currentIndexChanged.connect(self.modeChanged)

            for w in [self.ui.expressionDelay, self.ui.expressionDuration]:
                w.setFilters(QgsFieldProxyModel.Numeric)
                w.setLayer(layer.mapLayer)

        wth = [self.ui.expressionDelay, self.ui.expressionDuration]
        if t not in [ATConst.ITEM_CAMERA, ATConst.ITEM_GROWING_LINE]:
            wth += [self.ui.labelName, self.ui.lineEditName]

        if t != ATConst.ITEM_OPACITY:
            wth += [self.ui.labelOpacity, self.ui.doubleSpinBoxOpacity]

        if t != ATConst.ITEM_TEXTURE:
            if t != ATConst.ITEM_GROWING_LINE:
                wth += [self.ui.labelComboBox1, self.ui.comboBox1]

            wth += [self.ui.labelComboBox2, self.ui.comboBox2]

        if t != ATConst.ITEM_CAMERA:
            wth += [self.ui.labelNarration, self.ui.toolButtonAddImage, self.ui.toolButtonPreview, self.ui.plainTextEdit]

        if t == ATConst.ITEM_GROWING_LINE:
            wth += [self.ui.widgetTopBar]

        for w in wth:
            w.setVisible(False)

        self.resize(self.minimumSize())

        # set values
        self.ui.labelKFCount.setText("/ {}".format(self.kfCount))
        self.ui.slider.setMaximum(self.kfCount - 1)

        self.easingButtons[item.data(0, ATConst.DATA_EASING)].setChecked(True)

        idxFrom = min(track.indexOfChild(item), self.kfCount - 1)
        self.ui.slider.setValue(idxFrom)
        self.currentKeyframeChanged(idxFrom)

        # signal-slot
        self.ui.slider.valueChanged.connect(self.currentKeyframeChanged)
        self.ui.toolButtonPrev.clicked.connect(self.prevKeyframe)
        self.ui.toolButtonNext.clicked.connect(self.nextKeyframe)
        self.ui.toolButtonPlay.clicked.connect(self.play)
        self.ui.pushButtonPlayAll.clicked.connect(self.playAll)
        self.ui.toolButtonAddImage.clicked.connect(self.addImage)
        self.ui.toolButtonPreview.clicked.connect(self.showNarrativeBox)

        self.ui.lineEditDelay.editingFinished.connect(self.apply)
        self.ui.lineEditDuration.editingFinished.connect(self.apply)

    def prevKeyframe(self):
        self.ui.slider.setValue(self.ui.slider.value() - 1)

    def nextKeyframe(self):
        self.ui.slider.setValue(self.ui.slider.value() + 1)

    def currentKeyframeChanged(self, value):
        self.ui.lineEditCurrentKF.setText(str(value + 1))
        self.ui.toolButtonPrev.setEnabled(value > 0)
        self.ui.toolButtonNext.setEnabled(value < self.kfCount - 1)

        hasTrans = not self.isKF or value < self.kfCount - 1
        self.ui.toolButtonPlay.setEnabled(hasTrans)

        if self.currentItem and not self.isPlaying:
            self.apply()

        p = self.item.parent()
        item = p.child(value)
        self.currentItem = item

        self.easingButtons[item.data(0, ATConst.DATA_EASING)].setChecked(True)

        delay = str(item.data(0, ATConst.DATA_DELAY))
        duration = str(item.data(0, ATConst.DATA_DURATION))

        if self.type == ATConst.ITEM_GROWING_LINE:
            d = [delay, duration, str(0), str(DEF_SETS.ANM_DURATION)]

            if item.data(0, ATConst.DATA_SEQ):
                d = d[2:4] + d[0:2]
                self.ui.comboBox1.setCurrentIndex(1)
            else:
                self.modeChanged(0)

            self.ui.lineEditDelay.setText(d[0])
            self.ui.lineEditDuration.setText(d[1])
            self.ui.expressionDelay.setExpression(d[2])
            self.ui.expressionDuration.setExpression(d[3])
        else:
            self.ui.lineEditDelay.setText(delay)
            self.ui.lineEditDuration.setText(duration)
            self.updateTime(p, value)

        if self.isKF:
            nar = item.data(0, ATConst.DATA_NARRATION) or {}
            self.narId = nar.get("id")
            self.ui.plainTextEdit.setPlainText(nar.get("text") or "")

        if self.type == ATConst.ITEM_CAMERA:
            self.ui.lineEditName.setText(item.text(0))

        elif self.type == ATConst.ITEM_OPACITY:
            self.ui.doubleSpinBoxOpacity.setValue(item.data(0, ATConst.DATA_OPACITY))

        elif self.type == ATConst.ITEM_TEXTURE:
            idx = self.ui.comboBox1.findData(item.data(0, ATConst.DATA_MTL_ID))
            if idx != -1:
                self.ui.comboBox1.setCurrentIndex(idx)

            idx = self.ui.comboBox2.findData(item.data(0, ATConst.DATA_EFFECT))
            if idx != -1:
                self.ui.comboBox2.setCurrentIndex(idx)

        elif self.type == ATConst.ITEM_GROWING_LINE:
            self.ui.lineEditName.setText(item.text(0))

        if self.isKF and value >= self.kfCount - 2:
            for w in [self.ui.labelDelay, self.ui.lineEditDelay, self.ui.labelDuration, self.ui.lineEditDuration,
                      self.ui.labelComboBox2, self.ui.comboBox2, self.ui.labelBegin, self.ui.labelEnd,
                      self.ui.labelEasing] + list(self.easingButtons.values()):
                w.setEnabled(hasTrans)

        if not self.isPlaying:
            self.panel.tree.setCurrentItem(item)

    def updateTime(self, parentItem, index):

        def setUnknown():
            t = "unknown"
            self.ui.labelTimeBegin.setText(t)
            self.ui.labelTimeEnd.setText(t)
            self.ui.labelTotal.setText(t)

        if self.useExpression():
            return setUnknown()

        fmt = "{:.0f}:{:06.3f}"
        idxEnd = self.kfCount - 1 if self.isKF else self.kfCount
        total = 0

        try:
            for i in range(0, index):
                item = parentItem.child(i)
                total += item.data(0, ATConst.DATA_DELAY) + item.data(0, ATConst.DATA_DURATION)

            if index < idxEnd:
                begin = total + parentItem.child(index).data(0, ATConst.DATA_DELAY)
                end = begin + parentItem.child(index).data(0, ATConst.DATA_DURATION)
                total = end

                for i in range(index + 1, idxEnd):
                    item = parentItem.child(i)
                    total += item.data(0, ATConst.DATA_DELAY) + item.data(0, ATConst.DATA_DURATION)

                b = fmt.format(*divmod(begin / 1000, 60))
                e = fmt.format(*divmod(end / 1000, 60))
            else:
                b = e = ""

            self.ui.labelTimeBegin.setText(b)
            self.ui.labelTimeEnd.setText(e)
            self.ui.labelTotal.setText(fmt.format(*divmod(total / 1000, 60)))
        except:
            setUnknown()

    def useExpression(self):
        return bool(self.type == ATConst.ITEM_GROWING_LINE and self.ui.comboBox1.currentIndex())

    def modeChanged(self, index):
        b = bool(index)
        self.ui.expressionDelay.setVisible(b)
        self.ui.expressionDuration.setVisible(b)
        self.ui.lineEditDelay.setVisible(not b)
        self.ui.lineEditDuration.setVisible(not b)

        self.updateTime(self.item.parent(), self.ui.slider.value())

    def apply(self):
        if not self.type & ATConst.ITEM_MBR:
            return

        item = self.currentItem

        easing = self.ui.buttonGroup.checkedId()
        item.setData(0, ATConst.DATA_EASING, easing if easing >= 0 else ATConst.EASING_LINEAR)

        if self.useExpression():
            delay = self.ui.expressionDelay.expression() or "0"
            duration = self.ui.expressionDuration.expression() or str(DEF_SETS.ANM_DURATION)
        else:
            delay = parseInt(self.ui.lineEditDelay.text(), 0)
            duration = parseInt(self.ui.lineEditDuration.text(), DEF_SETS.ANM_DURATION)

        item.setData(0, ATConst.DATA_DELAY, delay)
        item.setData(0, ATConst.DATA_DURATION, duration)

        icon = None
        if self.type == ATConst.ITEM_CAMERA:
            item.setText(0, self.ui.lineEditName.text())

        elif self.type == ATConst.ITEM_OPACITY:
            opacity = self.ui.doubleSpinBoxOpacity.value()
            item.setText(0, "opacity '{}'".format(opacity))
            item.setData(0, ATConst.DATA_OPACITY, opacity)

        elif self.type == ATConst.ITEM_TEXTURE:
            item.setText(0, self.ui.comboBox1.currentText())
            item.setData(0, ATConst.DATA_MTL_ID, self.ui.comboBox1.currentData())
            item.setData(0, ATConst.DATA_EFFECT, self.ui.comboBox2.currentData())

        elif self.type == ATConst.ITEM_GROWING_LINE:
            item.setText(0, self.ui.lineEditName.text())
            item.setData(0, ATConst.DATA_SEQ, self.ui.comboBox1.currentData())
            icon = self.panel.tree.effectIcon

        if self.isKF:
            text = self.ui.plainTextEdit.toPlainText()
            if text:
                nar = {
                    "id": self.narId or ("nar_" + createUid()),
                    "text": text
                }
                icon = self.panel.iconNarration
            else:
                nar = None

            item.setData(0, ATConst.DATA_NARRATION, nar)

        item.setIcon(0, icon if icon else self.panel.tree.keyframeIcon)

        p = item.parent()
        self.updateTime(p, p.indexOfChild(item))

    def accept(self):
        if self.type & ATConst.ITEM_MBR:
            self.apply()
        QDialog.accept(self)

    def helpClicked(self):
        t = {ATConst.ITEM_CAMERA: "camera",
             ATConst.ITEM_OPACITY: "opacity",
             ATConst.ITEM_TEXTURE: "texture",
             ATConst.ITEM_GROWING_LINE: "growingline"
        }.get(self.type, "")
        openHelp(f"dlg=keyframe&type={t}")

    def addImage(self):
        filename = selectImageFile(self)
        if filename:
            url = QUrl.fromLocalFile(filename).toString()
            self.ui.plainTextEdit.insertPlainText('<img src="{}" width="100%">'.format(url))

    def showNarrativeBox(self):
        self.panel.showNarrativeBox(self.ui.plainTextEdit.toPlainText())

    def playAnimation(self, items):
        self.isPlaying = True
        self.panel.playAnimation(items)

        self.panel.tree.clearSelection()

        self.ui.toolButtonPlay.setIcon(self.panel.iconStop)
        self.ui.pushButtonPlayAll.setIcon(self.panel.iconStop)
        self.ui.pushButtonPlayAll.setText("")

    def stopAnimation(self):
        self.panel.stopAnimation()
        self.isPlaying = self.isPlayingAll = False

    def play(self):
        if not self.isPlaying:
            self.apply()

            if self.type & ATConst.ITEM_MBR:
                if self.currentItem:
                    self.playAnimation([self.currentItem])
        else:
            self.stopAnimation()

    def playAll(self):
        if not self.isPlaying:
            self.apply()

            if self.type & ATConst.ITEM_MBR:
                self.isPlayingAll = True
                self.playAnimation([self.item.parent()])
        else:
            self.stopAnimation()

    # @pyqtSlot()
    def animationStopped(self):
        self.ui.toolButtonPlay.setIcon(self.panel.iconPlay)
        self.ui.toolButtonPlay.setChecked(False)
        self.ui.pushButtonPlayAll.setIcon(self.panel.iconPlay)
        self.ui.pushButtonPlayAll.setText("Play All")
        self.ui.pushButtonPlayAll.setChecked(False)

        self.isPlaying = self.isPlayingAll = False

    # @pyqtSlot(int)
    def tweenStarted(self, index):
        if self.isPlayingAll:
            logger.debug("TWEENING %d ...", index)
            self.ui.slider.setValue(index)
