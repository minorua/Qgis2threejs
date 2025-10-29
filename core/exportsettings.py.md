core/exportsettings.py

minorua: このファイルを解析して、このコードの内容について詳しく解説して下さい。クラス名・メソッド名・変数名がわかりにくいものについては指摘して修正案を挙げて下さい。

GitHub Copilot: `exportsettings.py` は Qgis2threejs プラグインのコア設定管理を担うファイルです。主にエクスポート設定やレイヤー管理、シーン・カメラ・ウィジェット・アニメーションなどの情報を保持・操作します。以下、主要なクラス・メソッド・変数の解説と、分かりにくい命名への指摘・修正案を示します。

---

## 主なクラス

### 1. `BuildOptions`
- レイヤーのマテリアル関連オプションを保持する単純なクラス。
- 変数: `onlyMaterial`, `allMaterials`

### 2. `Layer`
- QGISプロジェクト内のレイヤー情報を保持。
- 主な属性: `layerId`, `name`, `type`, `properties`, `visible`, `jsLayerId`, `mapLayer`, `opt`
- 主なメソッド:
  - `material(mtlId)`: 指定IDのマテリアル取得
  - `mtlIndex(mtlId)`: 指定IDのマテリアルインデックス取得
  - `clone()`, `copyTo(t)`: レイヤーの複製
  - `toDict()`, `fromDict(obj)`, `fromQgsMapLayer(mapLayer)`: 辞書⇔オブジェクト変換

### 3. `ExportSettings`
- エクスポート全体の設定を管理。
- 主な属性: `data`, `mapSettings`, `crs`, `isPreview`, `jsonSerializable`, `localMode`, `nextJsLayerId` など
- 主なメソッド:
  - 設定のロード/保存: `loadSettings`, `loadSettingsFromFile`, `saveSettings`
  - シーン・カメラ・コントロール・レイヤー・ウィジェット・アニメーション関連の getter/setter
  - `updateLayers()`: QGISプロジェクトのレイヤー構成に合わせて内部レイヤーリストを更新
  - `getLayer(layerId)`, `addLayer(layer)`, `insertLayer(index, layer)`, `removeLayer(layerId)`: レイヤー操作
  - DEMプロバイダ関連: `demProviderByLayerId(id)`, `demGridSegments(layerId)`
  - アニメーション関連: `enabledValidKeyframeGroups`, `hasEnabledValidKeyframeGroup`, `animationData`, `setAnimationData`
  - 互換性維持: `loadEarlierFormatData(settings)`

---

## 分かりにくい命名と修正案

### クラス名
- `Layer` → `ExportLayer`（QGIS標準のLayerと混同しやすい）
- `BuildOptions` → `LayerBuildOptions`（何のBuildか明確化）

### 変数・メソッド名
- `opt`（Layer内）→ `buildOptions`
- `mtlIndex` → `materialIndex`
- `mtlId` → `materialId`
- `jsLayerId` → `exportLayerId`（JSとの連携用途を明確化）
- `toDict`/`fromDict` → `to_dict`/`from_dict`（PEP8準拠）
- `copyTo` → `copy_to`
- `clone` → `copy`（Python標準のcopyに合わせる）
- `data`（ExportSettings内）→ `settingsData`（何のデータか明確化）
- `isPreview` → `previewMode`
- `jsonSerializable` → `isJsonSerializable`
- `localMode` → `isLocalMode`
- `nextJsLayerId` → `nextExportLayerId`
- `updateLayers` → `syncLayersWithProject`
- `getLayer` → `findLayerById`
- `getLayerByJSLayerId` → `findLayerByExportId`
- `addLayer` → `appendLayer`
- `insertLayer` → `insertLayerAt`
- `removeLayer` → `deleteLayerById`
- `demProviderByLayerId` → `getDemProviderByLayerId`
- `demGridSegments` → `getDemGridSegments`
- `widgetProperties` → `getWidgetProperties`
- `setWidgetProperties` → `setWidgetProperties`
- `isNavigationEnabled` → `navigationEnabled`
- `setNavigationEnabled` → `setNavigationEnabled`
- `headerLabel` → `getHeaderLabel`
- `setHeaderLabel` → `setHeaderLabel`
- `footerLabel` → `getFooterLabel`
- `setFooterLabel` → `setFooterLabel`
- `isAnimationEnabled` → `animationEnabled`
- `enabledValidKeyframeGroups` → `getEnabledValidKeyframeGroups`
- `hasEnabledValidKeyframeGroup` → `hasEnabledValidKeyframeGroup`
- `animationData` → `getAnimationData`
- `setAnimationData` → `setAnimationData`
- `groupsWithExpressions` → `getGroupsWithExpressions`
- `narrations` → `getNarrations`
- `loadEarlierFormatData` → `loadLegacyFormatData`
- `calculateGridSegments` → `calculate_grid_segments`
- `deepcopyExcept` → `deepcopy_except`
- `urlFromPCLayer` → `getUrlFromPointCloudLayer`

---

## その他の指摘

- クラス・メソッド・変数名はPEP8に準拠すると可読性が向上します（例: `toDict` → `to_dict`）。
- `Layer` クラスはQGISの `QgsMapLayer` と混同しやすいので、用途を明確にする命名が望ましいです。
- `data` など汎用的な名前は、何のデータか明示することで保守性が高まります。

---

## まとめ

このファイルはQgis2threejsのエクスポート設定管理の中核です。命名規則を整理し、より明確な名前に変更することで、可読性・保守性が向上します。修正案を参考に、リファクタリングを検討してください。
