# web/js/src 配下のリファクタリング指摘

対象ディレクトリ: [web/js/src](../web/js/src)

以下は、現状の実装を静的に確認した結果から抽出した、主なリファクタリング候補です。各項目について「なぜ問題なのか」「修正案」を併記しています。

## 1. [web/js/src/app.js] の初期化処理が巨大で責務が混在している
### なぜ問題なのか
- [web/js/src/app.js](../web/js/src/app.js) の `app.init()` が、レンダラ作成、シーン作成、カメラ/コントロール初期化、UIイベント登録、ロード管理、クエリマーカー作成までを一つのメソッドに詰め込んでいます。
- 1つの変更で他の初期化処理に影響しやすく、テストや再利用が難しくなっています。

### 修正案
- `setupRenderer()`、`setupScene()`、`setupCameraAndControls()`、`setupEventListeners()`、`setupUi()` のように小さな関数へ分割する。
- 初期化順序を明示した `initialize()` ルートを用意し、依存関係を明確にする。

---

## 2. [web/js/src/app.js] の URL パラメータ解析が手続き的で脆弱
### なぜ問題なのか
- `window.location.search` と `hash` を文字列分割して処理しており、空値・重複パラメータ・型変換の扱いが曖昧です。
- 追加パラメータが増えるたびに分岐が増え、読みづらく保守しづらい構造です。

### 修正案
- `URLSearchParams` を使ってパラメータを一元的に解析する。
- `parseUrlParameters()` の戻り値を、数値や真偽値などの型を持つ正規化済みオブジェクトに変換する。

---

## 3. [web/js/src/gui.js] の UI ロジックと DOM 操作が散在している
### なぜ問題なのか
- [web/js/src/gui.js](../web/js/src/gui.js) では、ポップアップ制御、レイヤーパネル制御、印刷ダイアログ作成などが同じファイル内で密結合しています。
- DOM 要素の取得・追加・クラス制御が多く、UIの振る舞いを追うのが難しくなっています。

### 修正案
- `PopupController`、`LayerPanelController`、`PrintDialogController` のように、UIごとに責務を分離する。
- DOM 生成ロジックを `createElement()` ベースの小さなヘルパーへ寄せる。

---

## 4. [web/js/src/scene.js] の `loadData()` が長大で条件分岐が多い
### なぜ問題なのか
- [web/js/src/scene.js](../web/js/src/scene.js) の `loadData()` が、シーンデータ・レイヤーデータ・ブロックデータを同じメソッド内で処理しています。
- 追加のデータ種別が増えるたびに分岐が増え、読み取り性と拡張性が低下しています。

### 修正案
- `loadSceneData()`、`loadLayerData()`、`loadBlockData()` に分ける。
- レイヤー型の判定は `switch` 文またはマップを使って明示的に管理する。

---

## 5. [web/js/src/vectorlayer.js] のラベル生成ロジックが描画処理とデータ生成を同時に担当している
### なぜ問題なのか
- ラベルのテキスト作成、キャンバス描画、スプライト生成、コネクタ作成が一つのメソッド内に詰め込まれています。
- 1つのラベル処理に変更が入るたびに、ロジック全体を理解し直す必要があり、保守コストが高いです。

### 修正案
- `LabelRenderer` や `LabelBuilder` のような専用クラスに切り出す。
- 文字列描画処理を `createLabelTexture()` のような小さな関数へ分解する。

---

## 6. [web/js/src/vectorlayer.js] の図形生成ロジックが巨大で、オブジェクト種別ごとの責務が混在している
### なぜ問題なのか
- `LineLayer` や `PolygonLayer` の `createObjFunc()` が、Line / Thick Line / Pipe / Wall / Polygon / Extruded / Overlay など多くの生成パターンを抱えています。
- 新しい図形タイプを追加するたびに同じ関数が肥大化しやすく、テストも難しくなります。

### 修正案
- オブジェクト種別ごとに別のビルダー関数またはクラスを用意する。
- 生成戦略を `strategy` パターンのように分離し、条件分岐を減らす。

---

## 7. [web/js/src/material.js] の `Material.loadData()` がマテリアル種別ごとの分岐を一手に引き受けている
### なぜ問題なのか
- テクスチャ読み込み、透明度、ワイヤーフレーム、マテリアルタイプ選択、イベント登録などが一つのメソッド内にまとまっています。
- 各マテリアルタイプの振る舞いを個別にテストしづらく、将来の拡張にも弱いです。

### 修正案
- `createMaterialByType()` のようなファクトリ関数を追加し、型ごとの生成処理を分離する。
- テクスチャロードや透過設定などの共通処理は別メソッドに切り出す。

---

## 8. [web/js/src/demlayer.js] の DEM ブロック読み込み処理に重複が多い
### なぜ問題なのか
- [web/js/src/demlayer.js](../web/js/src/demlayer.js) の `DEMBlock`、`DEMTileBlock`、`ClippedDEMBlock` では、ファイル読み込み、ジオメトリ構築、メッシュ作成、マテリアル設定にかなりの重複があります。
- 同じ変更を複数箇所で反映しなければならず、バグの温床になります。

### 修正案
- 共通の `loadGridData()` や `createMeshFromGrid()` のようなヘルパーを導入し、重複処理を集約する。
- ブロック種別は差分だけを持たせ、共通部分は基底クラスに寄せる。

---

## 9. [web/js/src/model.js] のモデルキャッシュ管理が弱い
### なぜ問題なのか
- [web/js/src/model.js](../web/js/src/model.js) では、`clear()` が配列を空にするだけで、キャッシュ済みモデルや関連イベントの解放が行われていません。
- 長時間の表示切り替えや再読み込みでメモリを圧迫しやすく、リソース管理が曖昧です。

### 修正案
- `clear()` でキャッシュオブジェクトを破棄・クリアし、必要に応じて `dispose()` も実装する。
- モデルのロード状態とキャッシュ状態を責務ごとに分離する。

---

## 10. [web/js/src/utils.js] に古い Three.js API 依存のコードが残っている
### なぜ問題なのか
- `setGeometryUVs()` は `geom.vertices` や `geom.faces` を使っており、現行の BufferGeometry ベースの実装とは相性が悪いです。
- 使われていないコードや古い API 依存のまま残ると、今後の移行時に混乱を招きます。

### 修正案
- 使われていない関数は削除するか、現行 API に合わせて再実装する。
- 互換性が必要な場合は、明示的なコメントとテストを追加して旧実装との境界を明確にする。

---

## 優先度の目安
1. [web/js/src/app.js](../web/js/src/app.js) の初期化処理の分割
2. [web/js/src/scene.js](../web/js/src/scene.js) と [web/js/src/vectorlayer.js](../web/js/src/vectorlayer.js) の責務分離
3. [web/js/src/material.js](../web/js/src/material.js) と [web/js/src/demlayer.js](../web/js/src/demlayer.js) の重複排除
4. キャッシュ・リソース管理の改善

この整理は、まず「読みやすさ」と「拡張しやすさ」を優先してまとめたものです。実装に入る場合は、まず大きなファイルから段階的に分割すると負荷が低くなります。
