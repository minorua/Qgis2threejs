core/build/builder.py

minorua: このファイルを解析して、このコードの内容について詳しく解説して下さい。クラス名・メソッド名・変数名がわかりにくいものについては指摘して修正案を挙げて下さい。

GitHub Copilot: I'll create a short todo list to track the analysis steps, then read builder.py to analyze its classes, methods, and variables. Expected outcome: a parsed summary and rename suggestions. I'll start by writing the todo list.

Created 4 todos

次に builder.py を読み込みます。目的はクラス／メソッド／変数を抽出して説明するためのソース取得です。期待する結果：ファイル全体のテキスト。

Read [](file:///d%3A/Users/minorua/QGIS/plugins/Qgis2threejs/core/build/builder.py)

次にタスクの進捗を更新します：ファイル読み取りを完了にして、解析タスクを「進行中」にします。

Starting (2/4) *Analyze structure*

次にタスクの進捗を更新します：構造解析を完了にして、ドキュメント作成タスクを進行中にします。

Starting (3/4) *Document and explain*

以下は builder.py の解析結果（日本語）。読み取り済みの内容を要約し、各要素の役割、問題点、改善（リネーム）案を挙げます。作業の次のステップ案も最後に書きます。

## 概要（要点）
- このモジュールは Three.js 用の「シーン」オブジェクト（辞書）を構築するビルダーを提供します。
- 中心クラスは `ThreeJSBuilder`。設定 (`settings`) を元にシーン全体（プロパティ＋レイヤ群）を組み立て、レイヤごとのビルダー（DEMLayerBuilder / VectorLayerBuilder / PointCloudLayerBuilder）に処理を委譲します。
- ユーティリティ的に no-op の `dummyProgress` / `dummyLogMessage` が付属しています。
- `LayerBuilderFactory` は LayerType 別にレイヤビルダークラスをマップした定数（dict）です。

## 主要シンボル（クラス・関数）の解説

### LayerBuilderFactory (module-level)
- 役割：`LayerType`（列挙）をキーに、該当するレイヤビルダークラスを返す辞書。
- 注意点：定数なので名前は大文字（PEP8）で `LAYER_BUILDER_FACTORY` または `LAYER_BUILDER_MAP` の方が明確。
- 使用箇所：`ThreeJSBuilder.buildLayer` / `layerBuilders` で .get(...) を呼んで動的にビルダーを生成。

### class ThreeJSBuilder
- コンストラクタ: `__init__(self, settings, progress=None, log=None)`
  - `settings`: レイヤやシーン設定を持つオブジェクト（外部定義）。`self.imageManager = ImageManager(settings)` を保持。
  - `progress`: 進捗通知コールバック（省略時は `dummyProgress`）。
  - `log`: ログ用コールバック（省略時は `dummyLogMessage`）。
  - 内部フラグ `_canceled`：キャンセル管理。

- メソッド一覧（意図・挙動）
  - `buildScene(self, build_layers=True, cancelSignal=None)`
    - シーン（辞書）を組み立てて返す。
    - base extent, origin, zScale, ライト種類、フォグ、投影情報（CRS）などを `p`（プロパティ辞書）にまとめる。
    - `build_layers` が真なら `buildLayers(cancelSignal)` を呼んで `layers` を追加。
    - QGIS API 互換のため `crs.toProj4()` と `crs.toProj()` の条件分岐あり。
  - `buildLayers(self, cancelSignal=None)`
    - `settings.layers()` から visible なレイヤを列挙して各レイヤをビルドする。
    - 進捗コール `self.progress(percentage, msg)` を頻繁に呼ぶ。
    - `cancelSignal`（Qt のシグナル想定）を渡すと接続／切断を行い、キャンセル時に `self.cancel()` を呼ぶ。
  - `buildLayer(self, layer, cancelSignal=None)`
    - 単一レイヤをビルドする。`LayerBuilderFactory.get(layer.type, VectorLayerBuilder)(...)` で適切なビルダーを生成し、`.build()` を呼ぶ。
  - `layerBuilders(self, layer)`
    - 単一レイヤに対する「ビルダー」イテレータを返す。まずトップの builder を yield し、その builder.subBuilders() （複数の部分ビルダー）を順次 yield する。
    - 注意: 変数名の上書き（下方で for loop が同じ `builder` を再利用）という可読性・バグ源の恐れ。
  - `canceled` プロパティ（getter/setter）
    - getter: `_canceled` が False の場合に `QgsApplication.processEvents()` を呼んでイベント処理をしてから `_canceled` を返す（UI を生かすための trick）。
    - setter: `_canceled` を設定するだけ。
  - `cancel(self)`
    - `_canceled = True` をセット。

- 注意点（設計面）
  - `buildScene` 内で使うローカル変数名 `p`, `sp`, `be` は短すぎて可読性が低い（何を表すかすぐ分からない）。
  - `layerBuilders` 内で同じ変数名 `builder` を再利用している（外側の builder を上書き）。混乱するためバグを招きやすい。
  - `progress`/`log` がコールバックで受け取れるのは良いが、シグネチャが固定 (percentage, msg) であることが暗黙の前提。型・doc がない。
  - `LayerBuilderFactory` がモジュール直下のミュータブル辞書で定義されており、他所で書き換えられる可能性がある（用途によっては可変で良いが、意図がないなら frozendict 相当か UPPER_CASE 定義が望ましい）。

### dummyProgress / dummyLogMessage
- どちらも no-op（pass）。
- 名前は分かりやすいが、先頭にアンダースコアを付けるか、モジュール内で `NOOP_PROGRESS` のように定義しておくと意図が明確。

## 潜在的な問題・改善提案（詳細）

1. 変数名の不親切さ
   - 短名一覧：`p`, `sp`, `be`, `mapTo3d`, `obj`, `d`, `layer_list`（これは OK）
   - 改善案：
     - `p` -> `scene_props` または `scene_dict`
     - `sp` -> `scene_ui_props` または `scene_properties`
     - `be` -> `base_extent`
     - `mapTo3d` -> `map_to_3d`
     - `d` (fog slider value) -> `fog_slider_value`
     - `obj` (scene object) -> `scene_obj` / `scene_json`
   - 理由：可読性向上、後から読む人が辞書の意味を推測しなくて済む。

2. メソッド / クラス名のスタイル（PEP8）
   - Python の慣例ではメソッド名は snake_case。現在は `buildScene`, `buildLayers` などキャメルケース混在。
   - 改善案（推奨、ただし破壊的変更）：
     - `ThreeJSBuilder`（クラス名は PascalCase のままで問題なし）
     - `buildScene` -> `build_scene`
     - `buildLayers` -> `build_layers`
     - `buildLayer` -> `build_layer`
     - `layerBuilders` -> `iter_layer_builders` または `layer_builders`
     - `canceled` プロパティは `is_canceled` の方がブールとして直感的（ただし property の getter/setter 実装は変えずにエイリアスを作ることを提案）
   - リネームは呼び出し箇所が多数ある可能性があるため、まずは非破壊で「新しい名前の関数を追加して古い名前はラッパーとして残す」方式が安全。

3. 変数名の上書きバグ臭（確実に修正すべき）
   - `layerBuilders`:
     ```py
     builder = LayerBuilderFactory.get(...)(...)
     yield builder
     for builder in builder.subBuilders():
         yield builder
     ```
     外側の `builder` を内側の `for builder in ...` が上書きしている。これは意図的かもしれないが可読性が非常に悪い。推奨：
     ```py
     root_builder = ...
     yield root_builder
     for sub_builder in root_builder.subBuilders():
         yield sub_builder
     ```

4. 定数名のスタイル
   - `LayerBuilderFactory` を `LAYER_BUILDER_FACTORY` または `LAYER_BUILDER_MAP` にするのが一貫性がある（モジュール定数は大文字）。

5. QGIS API の互換判定
   - 行：
     ```py
     p["proj"] = crs.toProj4() if Qgis.QGIS_VERSION_INT < 31003 else crs.toProj()
     ```
   - コメント：`toProj4()` は古い API、`toProj()` に移行している。より堅牢にするなら try/except AttributeError か hasattr チェックを使う案もある（QGIS バージョン定数に依存しない）。

6. Progress 計算の潜在的注意点
   - `self.progress(int(i / total * 80) + 10, "Building {} layer...".format(layer.name))`
     - `total` が 0 のときはそもそも for ループに入らないため ZeroDivisionError は発生しない。ただし仮に他で `total` を使う場合は警戒。
   - `i / total * 80` は浮動小数で計算され int() で丸めている。見た目は OK。

7. 無名関数（dummy）の扱い
   - `dummyProgress` / `dummyLogMessage` を簡潔に `_noop_progress` / `_noop_log` として定義しておくと読みやすい。あるいは `lambda *args, **kwargs: None`。

## 提案：リネーム一覧（原名 -> 推奨名 + 理由・影響度）
以下は「読みやすく」「Python慣習に沿った」名前案。影響度は「低／中／高」で、低は変更が局所的、 高はプラグインAPIや外部参照を多数変える可能性あり。

- LayerBuilderFactory -> LAYER_BUILDER_MAP（影響度：低）
  - 理由：定数であることを明示、PEP8。

- ThreeJSBuilder -> ThreeJsBuilder もしくは ThreeJsSceneBuilder（影響度：中）
  - 理由：大きくは変えなくてよいが `ThreeJS` の JS 大文字表記方針を `ThreeJs` に統一すると可読性（ただし既存外部参照があれば注意）。

- buildScene -> build_scene（影響度：高）
  - 破壊的。代替案: 新 API `build_scene()` を追加し、既存 `buildScene()` は `return self.build_scene(...)` としてデプリケート。

- buildLayers -> build_layers（影響度：高）
- buildLayer -> build_layer（影響度：高）
- layerBuilders -> iter_layer_builders または layer_builders（影響度：高）
  - 理由：snake_case とイテレータであることを明示。

- canceled (property) -> is_canceled（影響度：中）
  - 理由：ブールを返すプロパティは `is_` を付けると明確。互換性のため `canceled` を残して alias 実装にする。

- _canceled -> _is_canceled（影響度：低）
  - 内部変数名の明示。

- imageManager -> image_manager（影響度：中）
  - 理由：属性名は snake_case。

- p -> scene_props / scene_dict（影響度：低）
- sp -> scene_properties（影響度：低）
- be -> base_extent（影響度：低）
- mapTo3d -> map_to_3d（影響度：低）
- obj -> scene_obj（影響度：低）
- d -> fog_slider_value（影響度：low）

- dummyProgress -> _noop_progress / NOOP_PROGRESS（影響度：低）
- dummyLogMessage -> _noop_log / NOOP_LOG（影響度：低）

- `for builder in builder.subBuilders():` -> `for sub_builder in root_builder.subBuilders():`（影響度：低だが必須修正）
  - 理由：変数上書きを避けるため。

## 最小の安全な変更手順（推奨）
1. 可視性・非破壊の改善から着手：
   - `layerBuilders` の変数上書きは即修正（低リスク）。
   - `p`, `sp`, `be` 等のローカル変数を明示名に変更（関数内修正、比較的低リスク）。
   - `LayerBuilderFactory` -> `LAYER_BUILDER_MAP` にリネーム（モジュール内のみなら低リスク。ただし他ファイルで参照しているなら同時に更新が必要）。
2. 次に API 名（メソッド名）の snake_case 移行を非破壊に行う：
   - 例：`def build_scene(...): return self.buildScene(...)` として新しい名前を追加し、将来 deprecate を通す。
3. （必要であれば）大規模リネームをリファクタリングツールや repo-wide search/replace で一括実施。テスト（もしあれば）を走らせる。

## 小さな改善・追加推奨
- 各メソッドに短い docstring を追加（引数、返り値、キャンセルの扱い）。
- type hints を付ける（可能なら `-> dict` など）。
- `dummyProgress` / `dummyLogMessage` を明示的に no-op logger へ差し替えるか、`logging` モジュールに接続できるようにする。
- `crs.toProj4()` / `crs.toProj()` の判定は `hasattr(crs, "toProj")` 等で堅牢化。
- `LayerBuilderFactory` を外部からモック／拡張したい場合はファクトリ登録 API を提供すると良い（プラグイン拡張性向上）。

## 契約（contract）短く
- 入力：`settings`（レイヤ配列、シーン設定、CRS、mapTo3d 等を提供するオブジェクト）、オプション `progress` コールバック、`log` コールバック。
- 出力：Three.js用のシーン辞書（Python dict）を返す（JSON 化可能）。
- 成功基準：返される dict が viewer 側で使えるプロパティ群（type='scene', properties, layers）を持つ。
- エラー/例外：各レイヤビルダーの `.build()` が例外を吐いた場合は上流で捕まえてログを残すべき（現在は例外処理が見当たらない）。

## 代表的なエッジケース
- `settings.layers()` が空：`buildLayers` は空リストを返す（良い）。
- `cancelSignal` が渡されない：`cancel` メソッドでフラグを設定することでキャンセル可能。
- `crs` が None または `toProj`/`toProj4` が無い：現在は `settings.needsProjString()` が真の場合に `crs` を前提にしているので、ここは安全だが追加チェックは有益。
- imageManager が失敗する、あるいはレイヤビルダーが予期しない型を返す場合：例外やログ処理の強化を推奨。

## 例：具体的な安全修正パッチ（説明のみ）
- 変数上書き修正（`layerBuilders`）は即適用可能で、リスクが低いためまず適用することをおすすめします。
- メソッド名のスネーク化は互換性保持のためラッパーを置く形で段階導入するのが安全です。

---

## 進捗／次の提案（私からできること）
現在のタスクは「ドキュメント作成中」です（todo を更新済み）。次に私が実行できること（あなたが望めば即実行します）：
1. `layerBuilders` の変数上書き修正を apply_patch で行う（低リスク）。
2. ローカル変数名（`p`, `sp`, `be`, `mapTo3d` 等）を分かりやすい名前へ変更する小パッチを作成する（関数内の変更のみ）。
3. さらに進めて、メソッド名の snake_case 版を非破壊に追加するパッチ（ラッパー実装）を作る。
4. 変更後に関連する単体的なテストや簡単なスクリプト実行で動作確認（できる範囲で）。

どれを実行しましょうか？（最小で「1. 変数上書き修正」の適用を推奨します。）