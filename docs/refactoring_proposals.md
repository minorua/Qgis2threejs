# Qgis2threejs リファクタリング提案まとめ

このドキュメントは、コードベースを俯瞰しつつ、主に Python 側（core/controller/gui/utils）を中心に、継続的改善につながるリファクタリング候補を整理したものです。それぞれについて「なぜ問題なのか」「修正案」を示します。第三者ライブラリ（web/js/lib 配下）は対象外とします。

## タスク管理・データ送受信

- 問題: コントローラの送信キューがバックプレッシャなしで増殖
  - 参照: `core/controller/controller.py` の `appendDataToSendQueue()` で、キュー長が 1 を超えると警告が連発。ログ（`qgis2threejs.log`）でも "Sending/loading data is busy" が多数出力され、Web 側のロード完了 (`dataLoaded`) を待つ前にビルダーが大量のブロックデータを発行している。
  - なぜ問題か: UI 応答性の低下、メモリ使用量増加、ログスパム。大規模レイヤで顕著。テストの不安定化要因にもなる。
  - 修正案:
    - キュー上限値の導入とドロップ/マージ戦略（古いブロックを捨てる、複数ブロックをまとめて送る）。
    - ビルダー側でブロックを一定サイズにバッチング。`ThreeJSBuilder.buildLayerSlot()` で `blockBuilders()` を逐次発行するのではなく、進捗と併せてまとめ送信するインターフェースを追加。
    - `sendQueuedData()` にレート制御（タイマー、1 tick 1 送信）と、`isDataLoading` に応じたキュー投入抑制。

- 問題: タスク完了と送信完了の最終化が分離され複雑
  - 参照: `TaskManager` と `Q3DController` の `allTasksFinalized()`/`_tasksAndLoadingFinalized()` の条件分岐。タスクとロード完了の同期が取りづらい。
  - なぜ問題か: 状態遷移が読みにくく、保守コスト増。イベント競合時に完了通知の順序が前後する可能性。
  - 修正案:
    - 「タスク完了」→「送信完了」→「最終化」の 3 段階を 1 つのステートマシンに統合。`SceneLoadStatus` を強化して状態を単一の真理値表で管理。
    - `dataLoaded()` 側から常に `maybeFinalize()` を呼び、ガード下で一度だけ最終化する関数に集約。

- 問題: `TaskManager` の 1ms タイマー駆動
  - 参照: `core/controller/taskmanager.py` の `QTimer.setInterval(1)`。
  - なぜ問題か: ポーリング的挙動となり CPU 負荷/電力消費増。Qt のイベント駆動思想と相性が悪い。
  - 修正案:
    - タスク投入/完了イベントでのみ次タスクを起動する（`singleShot(0)` で次のイベントループへ）。固定 1ms 間隔を廃止。

## 例外処理・エラー伝搬

- 問題: `Q3DController.executeTask()` の広域例外キャッチが `TaskManager` に失敗を伝搬しない
  - 参照: `core/controller/controller.py` の `executeTask()` 末尾 `except Exception` ブロックがログ出力のみ。
  - なぜ問題か: コントローラ側で例外が起きた場合、キューが停滞しテストが不安定化。
  - 修正案:
    - `self.taskManager.taskFailed(target, traceback_str)` を呼び、続けて `self.taskManager.taskFinalized()` 相当の最終化を保証。target は `scene`/`layer.name`/`script` など文脈で決定。
    - 可能なら例外を特定（`ValueError`/`KeyError`/`RuntimeError` 等）に限定し、復旧可能なケースは明示的に処理。

- 問題: 広範な `except Exception as e` の多用
  - 参照: `grep` 結果（`gui/window.py`, `core/processing/procalgorithm.py`, `core/exportsettings.py` など）。
  - なぜ問題か: 本来検知すべき不整合を握りつぶすため、バグ検出が遅れる。テストが通っても実運用で落ちる可能性。
  - 修正案:
    - 例外の粒度を絞る。入出力は `IOError`/`OSError`、設定パースは `json.JSONDecodeError`、式評価は `QgsExpressionError` など、想定される型で捕捉。
    - ログには必ずスタックトレース（`traceback.format_exc()`）を出す。UI へは要約を通知。

## データモデル・命名

- 問題: `Layer.toDict()` の `geomType` 命名不一致
  - 参照: `core/exportsettings.py` の TODO コメント。
  - なぜ問題か: JSON スキーマの意味的な揺れがあり、将来のスキーマ変更時にバグの温床。
  - 修正案:
    - バージョン付きスキーマへ移行（例: `schemaVersion: 3`）。`geomType` → `type` へ段階的移行し、ロード時に旧→新フィールドをマッピング。

- 問題: dict ベースのプロパティ乱用
  - 参照: `Layer.properties` やビルダー周りでの文字列キー操作。
  - なぜ問題か: 型安全性が低く、IDE 補完や静的解析が弱い。テスト容易性も下がる。
  - 修正案:
    - `dataclasses`（もしくは `TypedDict`）でプロパティ構造を型付け。ビルダー入力を明確に。

## ビルダー・素材管理

- 問題: `DataManager.build()` の未定義変数参照の可能性
  - 参照: `core/build/datamanager.py` の TODO（`imgIndex` 未定義の可能性）。
  - なぜ問題か: 条件分岐により URL 指定時などで `imgIndex` を持たないケースがあり得る。
  - 修正案:
    - `imgIndex` の存在チェックを追加し、`base64`/`write` 分岐では `imgIndex is not None` を前提に処理。URL 指定時はファイル書き出しをスキップする安全ガードを入れる。

- 問題: ブロック単位送信の過多
  - 参照: `ThreeJSBuilder.buildLayerSlot()` で `blockBuilders()` を都度 `dataReady.emit`。
  - なぜ問題か: 大量イベントが GUI/ブリッジに負荷。Qt/JS 間のブリッジ帯域がボトルネックに。
  - 修正案:
    - ブロックを一定件数でまとめるバッチング。もしくはストリーム形式で Web 側が読み取れる API を設計。

## DEM プロバイダ

- 問題: NumPy 依存と不適切なログレベル
  - 参照: `core/demprovider.py` の TODO と `logger.error` の開発向け出力（`nodata`, `first value`）。
  - なぜ問題か: 依存削減の方針に反し、またエラー扱いで常時ノイズが出る。
  - 修正案:
    - NumPy 非依存のパスを用意（遅延インポート/フォールバック）。ログは `debug` に変更し、実運用では出さない。

## ログ設定

- 問題: インポート時の副作用（グローバル設定）
  - 参照: `utils/logging.py` の `configureLoggers()` がモジュール読み込み時に実行される。
  - なぜ問題か: テストやヘッドレス環境で意図しないハンドラが登録される。切替がしにくい。
  - 修正案:
    - 明示的初期化（起動時/テストセットアップ時）に限定。既存の `logger`/`web_logger` は遅延取得にし、必要に応じて `getLogger()` を呼ぶ。

## Web ビュー選択のグローバル状態

- 問題: インポート時に `Q3DView`/`Q3DWebPage` が決定される
  - 参照: `gui/webview.py`。
  - なぜ問題か: 実行時設定変更（WebEngine/WebKit の切替）に弱い。テストでモックしづらい。
  - 修正案:
    - ファクトリ関数化して、必要時に `setCurrentWebView()` を呼ぶ。グローバル変数は最小化。

## ユーティリティの品質

- 問題: 到達不能コード（dead code）
  - 参照: `utils/utils.py` の `shortTextFromSelectedLayerIds()` は早期 `return` 後に別実装が残置。
  - なぜ問題か: 読み手に混乱を与え、将来的な仕様変更時に誤用の恐れ。
  - 修正案:
    - 早期 `return` 以降の分岐を削除し、 1 実装に統一。

- 問題: 例外詳細の欠落
  - 参照: `core/build/vector/layer.py` の `readOpacity()` で `val` 未定義のままログ。
  - なぜ問題か: 障害解析が困難。
  - 修正案:
    - `except Exception as e:` とし、式文字列/例外内容をログに含める（例: `Wrong opacity expression: {expr}, error: {e}`）。

## スレッド/終了処理

- 問題: スレッド終了の責務分散
  - 参照: `Q3DController.teardown()` が builder をメインスレッドへ戻すロジックを持つ。
  - なぜ問題か: 終了手順のテスタビリティが低い。責務が広い。
  - 修正案:
    - Builder にコンテキスト管理/`close()` を用意し、終了処理をカプセル化。コントローラからは明示的な `quitRequest` のみ。

## テスト容易性

- 問題: 依存のハードコード（QGIS/Qt オブジェクト）
  - なぜ問題か: ヘッドレス/CI での単体テストが難しい。
  - 修正案:
    - 依存注入（DI）を適用し、`QgsProject`/`QWeb*` をインターフェース越しにモック可能にする。`utils.logging` もハンドラ差替えを容易に。

## 推奨する着手順（小さく始める）

1. 例外伝搬の一貫化: `Q3DController.executeTask()` での失敗ハンドリング追加。
2. ユーティリティの明確化: `shortTextFromSelectedLayerIds()` と `readOpacity()` の安全化。
3. ログ副作用の排除: `configureLoggers()` の遅延初期化化。
4. 送信キューのレート制御: `sendQueuedData()` に簡易レート制御と上限を導入。
5. スキーマ整備: `geomType` → `type` への段階的移行計画。

---

この提案は、既存の動作を壊さないように段階的に進める前提です。各段階でユニットテスト／統合テスト（`tests/unit` および `tests/gui`）を併走させ、パフォーマンスと安定性を計測・可視化しながら進めることを推奨します。
