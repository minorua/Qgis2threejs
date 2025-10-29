core/build/vector/feature.py


minorua: このファイルを解析して、このコードの内容について詳しく解説して下さい。クラス名・メソッド名・変数名がわかりにくいものについては指摘して修正案を挙げて下さい。

GitHub Copilot: 作業の計画と進捗管理のため、解析タスクを分割したtodoリストを作成します — これで各ステップの状態を追跡します。

Created 5 todos

進捗：todoリストを作成しました（「ファイル解析開始」が in-progress）。これから `feature.py` の詳細解析と説明を書きます。

## 概要
対象ファイル: feature.py（添付の抜粋全文に基づく）

このモジュールは Qgis2threejs の内部で、地物（feature）のジオメトリとプロパティを 3D 形式（TIN, Polygon, Line, Point など）に変換する責務を持つクラス `Feature` を定義しています。QGIS の `QgsGeometry` 相当の `self.geom` を受け取り、出力用途（地表モデル、押し出し、多角形オーバーレイ など）に合わせた変換処理を行います。

以下、コード構造ごとに分解して説明します。

## モジュール先頭のマッピングとインポート
- from .object import ObjectType
  - `ObjectType` はオブジェクトの種類（Polygon, Extruded など）を表す enum/クラスと推測されます。
- from ...const import LayerType, PropertyID as PID
  - `LayerType`：レイヤ種類（POINT, LINESTRING, POLYGON）。
  - `PropertyID (PID)`：プロパティ識別子（ALT や C2 など）を表す定数群。
- from ...geometry import VectorGeometry, PointGeometry, LineGeometry, PolygonGeometry, TINGeometry
  - 各 Geometry クラスは QGIS ジオメトリを 3D 用データ構造に変換する機能を持つ。

- LayerType2GeomClass: LayerType を受け取り、対応するクラスを返す辞書（POINT→PointGeometry など）
  - 目的：レイヤ種別が POINT/LINE の場合に単純に対応クラスを選んで変換できるようにする。

## クラス Feature — 概要
クラス定義（抜粋）:

class Feature:
    def __init__(self, vlayer, geom, props, attrs=None):
        self.layerType = vlayer.type
        self.ot = vlayer.ot
        self.geom = geom            # QgsGeometry と思われる
        self.props = props          # dict
        self.attributes = attrs     # list or None
        self.material = self.model = None

役割：
- レイヤ・地物に紐づく情報（ジオメトリ、プロパティ、属性、出力オブジェクトタイプ）を保持。
- clipGeometry / geometry / prop / hasProp といったユーティリティで 3D 変換処理を行う／補助する。

### __init__ の引数とメンバ
- vlayer: 上位の「仮想」レイヤオブジェクト。少なくとも `type`（LayerType 相当） と `ot`（ObjectType 相当） を持つ。
- geom: QGIS のジオメトリオブジェクト（self.geom）
- props: 辞書。PropertyID（PID）をキーにしたプロパティ（例えば ALT、高度など）。
- attrs: 属性リスト（optional）
- material, model: 後で設定される出力用の参照（ここでは None で初期化）

メモ: 命名は短いが意味が推測できる。ただし `ot` は曖昧。

## メソッド詳細

### clipGeometry(self, extent)
処理:
1. extent.rotation() を呼ぶ（extent は矩形範囲オブジェクトで、回転角を持つ）
2. 回転がある場合、ジオメトリを回転して extent 中心を基準に回す
3. self.geom = self.geom.clipped(extent.unrotatedRect())
   - unrotatedRect() は回転を取り除いた矩形（切り出し矩形）
4. 回転があれば、逆回転して元に戻す
5. 最後に修正済みの self.geom を返す

入力: extent（回転情報と unrotatedRect() と center() を持つ想定）
出力: 切り出した（かつ元の向きに戻した）ジオメトリ

注意点／エッジケース:
- extent.rotation() が 0 なら回転処理をスキップ
- self.geom.rotate() や clipped() の振る舞いに例外があれば扱う必要あり
- `self.geom` を破壊的に置換している（副作用）ので、呼び出し側がそれを期待しているか注意が必要

### geometry(self, z_func, mapTo3d, useZM=VectorGeometry.NotUseZM, baseExtent=None, grid=None)
最も大きく複雑な関数。目的は QGIS ジオメトリ（self.geom）を、レイヤ種別やオブジェクト種別、DEM（grid）などの条件に応じて適切な 3D ジオメトリ（PointGeometry / LineGeometry / PolygonGeometry / TINGeometry 等）に変換して返すこと。

主要ステップ：
1. alt = self.prop(PID.ALT, 0)
   - プロパティから高さオフセットを取得。無ければ 0。
2. zf = lambda x, y: z_func(x, y) + alt
   - 基本の z 関数（DEM 高さなど）に altitude を加えた関数を生成。
3. transform_func = mapTo3d.transform
   - map→3D の座標変換関数を取得。

4. 非 POLYGON レイヤ（POINT / LINESTRING）の場合:
   - LayerType2GeomClass[self.layerType].fromQgsGeometry(self.geom, zf, transform_func, useZM=useZM)
   - 簡潔に対応クラスの fromQgsGeometry を呼ぶ。

5. POLYGON レイヤの場合:
   - objType = type(self.ot)
   - if objType == ObjectType.Polygon:
       return TINGeometry.fromQgsGeometry(..., drop_z=(useZM == VectorGeometry.NotUseZM))
     - ここは「TIN (Triangulated Irregular Network) 形式」を生成（おそらくポリゴンを地表として扱う）
   - if objType == ObjectType.Extruded:
       return PolygonGeometry.fromQgsGeometry(..., useCentroidHeight=True, centroidPerPolygon=True)
     - 押し出しオブジェクト（建物など）を生成（重心の高さ利用）
   - # Overlay
     border = bool(self.prop(PID.C2) is not None)
     if grid is None:
         g = TINGeometry.fromQgsGeometry(self.geom, zf, transform_func, drop_z=True)
         if border:
             g.bnds_list = PolygonGeometry.fromQgsGeometry(self.geom, zf, transform_func).toLineGeometryList()
         return g
     # relative to DEM
     transform_func = mapTo3d.transform  # 再代入（実際は変化なし）
     if baseExtent.rotation():
         self.geom.rotate(baseExtent.rotation(), baseExtent.center())
     polys = grid.splitPolygon(self.geom)
     g = TINGeometry.fromQgsGeometry(polys, zf, transform_func, use_earcut=True)
     if border:
         bnds = grid.segmentizeBoundaries(self.geom)
         g.bnds_list = [LineGeometry.fromQgsGeometry(bnd, zf, transform_func, useZM=VectorGeometry.UseZ) for bnd in bnds]
     return g

説明ポイント:
- objType として ObjectType の種類により振る舞いを分岐（Polygon / Extruded / Overlay）
- `border` はプロパティ PID.C2（境界の色やスタイルなど）存在チェックで、境界線要素の生成を決定
- grid が None の場合は絶対 Z（DEM を使わない）で TIN を作り、必要であれば境界線も含める
- grid 非 None の場合は DEM 相対（地形に合わせた）処理。baseExtent の回転を考慮してジオメトリを回す。grid.splitPolygon で分割して TIN を生成。必要なら境界を segmentize して LineGeometry を生成。

注意点／エッジケース:
- 関数の途中で `transform_func = mapTo3d.transform` を2回設定しているが副作用はない（不要な再代入）。
- `self.geom` をメソッド内で回転（破壊的変更）する箇所がある（baseExtent.rotation() のとき）。呼び出し側にとって副作用になる可能性あり。
- `drop_z` の扱いは useZM フラグに依存しているが、境界処理では useZM が強制される場所がある（LineGeometry.fromQgsGeometry(..., useZM=VectorGeometry.UseZ)）。
- `grid.splitPolygon` の戻り値が単一ポリゴンか複数か（polys）で処理が期待通りか確認が必要。

### prop(self, pid, def_val=None)
- 単純に self.props.get(pid, def_val) を返すヘルパ。
- 意味: プロパティの取得（無ければデフォルト）

### hasProp(self, pid)
- pid が self.props に含まれるかどうかを返す。単純。

## 可読性・設計上の指摘と改善案
以下は識別子や設計でわかりにくい／改善余地がある点と提案です。

1. `ot`
   - 問題: 名前が短く意味が直感的でない（object type? overlay type?）。
   - 提案: `object_type` または `output_type`（用途に応じて）に変更。
   - 影響: 所有者クラスや vlayer の API と一致させる必要あり（リファクタするなら検索と置換を慎重に）。

2. `geom`
   - 現状でも広く使われる名前だが、どの種のジオメトリか明示があると良い。
   - 提案: `qgs_geom` / `qgs_geometry`（QGIS のジオメトリであることを明示）。

3. `props`
   - `properties` の方が読みやすい（特に `prop()` と混在するとき）。
   - 提案: `properties`。`prop(pid)` メソッド名は残してよい。

4. `prop` / `hasProp`
   - `prop` は短いが `get_property` の方が明確。`has_property` も同様。
   - ただし既存コードが多用していれば API 変更は注意。

5. `zf`, `g`, `bnds`, `polys`, `border`
   - `zf` → `z_func_with_altitude` や `z_with_alt`（冗長ではあるが意味明示）
   - `g` → `tin_geom` / `tin`（返すジオメトリの型に合わせる）
   - `bnds` → `boundaries` や `segmented_boundaries`
   - `polys` → `split_polygons`

6. geometry() の長さと複雑さ
   - 問題: 単一メソッドが多くの分岐を持ち、責務が多い（非ポリゴン / ポリゴンの処理、Overlay、DEM 相対、border オプションなど）。
   - 提案: geometry() を小さなメソッドに分割する。
     - e.g. _geometry_non_polygon(...), _geometry_polygon_tin(...), _geometry_polygon_extruded(...), _geometry_polygon_overlay(...).
   - 利点: 単体テストが容易になり、各ケースの副作用（self.geom の回転等）を局所化できる。

7. 副作用（self.geom の回転と置換）
   - 問題: clipGeometry と geometry（DEM 相対の部分）で self.geom を変更している。呼び出し側が元のジオメトリを必要とする場合、問題を起こす可能性あり。
   - 提案:
     - 回転や切り出しはコピーしたジオメトリで行う（if the geometry object supports copy()）。
     - もしくはドキュメントでこのメソッドがインプレース（破壊的）であることを明記する。

8. 冗長な再代入
   - `transform_func = mapTo3d.transform` が二回出現。二回目は不要。
   - 修正: 1回だけ上で定義すれば良い。

9. 型注釈と docstring
   - 提案: 各メソッドに簡潔な docstring（引数の型／戻り値／副作用）を追加。
   - Python typing を使い、引数と戻り値に型注釈を付ける（IDE と静的解析に有用）。

10. 可読性向上の小改変（例）
- 早期リターン / 分岐の整理でネストを浅くする。
- 変数名を分かりやすくし、長い式を意図のわかる関数呼び出しに置き換える。

## 小さなリファクタ例（擬似コード、編集ではない）
以下は `geometry()` の一部を分割して読みやすくする例（説明用）。実際にファイルを変更する際は test を用意してください。

- 変更前（抜粋）:
  zf = lambda x, y: z_func(x, y) + alt
  transform_func = mapTo3d.transform
  if self.layerType != LayerType.POLYGON:
      return LayerType2GeomClass[self.layerType].fromQgsGeometry(...)

- 変更後（概念）:
  z_with_alt = lambda x, y: z_func(x, y) + alt
  transform = mapTo3d.transform
  if self.layerType != LayerType.POLYGON:
      return self._geometry_for_point_or_line(z_with_alt, transform, useZM)
  # polygon branch
  if self._is_polygon_tin():
      return self._geometry_polygon_tin(z_with_alt, transform, useZM)
  if self._is_polygon_extruded():
      return self._geometry_polygon_extruded(z_with_alt, transform, useZM)
  return self._geometry_polygon_overlay(...)

メリット: 各ヘルパーメソッドに docstring と明確な名前を与えられる。

## テストと品質ゲート（推奨）
- 単体テスト（pytest 等）:
  - 非ポリゴン（POINT/LINE）からの変換が期待通りのクラスを返す。
  - ポリゴンで ObjectType.Polygon → TIN が返る（drop_z の振る舞い含む）。
  - ポリゴンで Extruded → PolygonGeometry が返る（centroid フラグ）。
  - grid が None と有り場合で境界（bnds_list）の有無を確認。
  - clipGeometry の回転が正しく適用されるか（回転 0 / 非 0）
- 静的解析:
  - 型注釈を追加し pyright / mypy を通す（repo に pyrightconfig.json があるので pyright を使うのが自然）。
- リント:
  - 変数名や未使用の再代入（transform_func の二重代入）を直す。

## 推奨する具体的命名変更まとめ（短表）
- ot → object_type（または output_type）
- geom → qgs_geometry
- props → properties
- prop(pid) → get_property(pid, default=None)
- hasProp(pid) → has_property(pid)
- zf → z_with_alt
- g → tin_geom
- bnds → boundaries / boundary_geometries
- polys → split_polygons

（API 変更は影響範囲が広いため、段階的に行い、互換性のために暫定のラッパーを残すことを推奨）

## 済んだことと次のステップ
- 済み：ソースの解析と詳細説明、改善点の提案まで完了（todo の 1 を in-progress のまま開始）。
- 次：詳細解説の残りタスク（`詳細解説作成` を完了扱いにする）と、必要なら簡単なコード例（リファクタ例）を提示します。もし望めば、実際に小さなリファクタ（変数名変更や冗長箇所の削除）をパッチで作成してテストを実行します — その場合はどの変更を優先するか指示ください。

ご希望があれば、上記の「小さなリファクタ例」を実ファイルに適用して単体テストを追加・実行します（変更は段階的に行い、CI 互換を保ちます）。どの提案を実装しましょうか？また、命名のみの変更を希望するか、メソッド分割まで進めるか教えてください。