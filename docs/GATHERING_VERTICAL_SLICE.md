# GATHERING_VERTICAL_SLICE

## 概要

本スライスでは、ロケーション依存の採取ポイントから素材を獲得し、既存の inventory / crafting / save / playable loop に接続する最小実装を追加する。

- 採取ポイント定義: `data/master/gathering_nodes.sample.json`
- 採取基盤: `game/gathering/*`
- Playable統合: `game/app/application/playable_slice.py`

## 今回の対応範囲

- マスターデータから採取ポイント定義をロード
- 現在地に存在する採取ポイント一覧表示
- 採取実行と採取結果の解決
- 採取結果を inventory へ反映
- `repeatable=false` ノードの再採取防止（同一セーブ中）
- Save/Load で採取済み node_id を保持
- 採取素材を既存クラフト判定にそのまま利用

## データ契約

### gathering_nodes.sample.json

各ノードは以下の最小項目を持つ。

- `node_id`
- `location_id`
- `name`
- `node_type`
- `description`
- `loot_entries`
  - `item_id`
  - `quantity`
  - `drop_type` (`guaranteed` / `chance`)
  - `chance` (`drop_type=chance` の場合)
- `repeatable`
- `unlock_flags`（任意）

### save_data_v1 の扱い

採取ポイント定義自体は保存しない。
ランタイム状態のみ `meta.gathering_state.gathered_node_ids` に保持する。

## 実行方法

- 自動テスト: `python -m unittest tests.test_gathering_slice`
- Playable CLI: `python -m game.app.cli.run_game_slice`
  - メニュー: 「採取ポイントを確認する」「採取する」

## スコープ外

- 時間経過によるリポップ
- 採取専用ツール/耐久
- レア演出やミニゲーム
- 天候・時間帯依存

## 次の拡張ポイント

- `repeatable=true` ノードの再採取ルール（クールダウン/日次更新）
- クエスト進行や会話選択による採取ノード追加解放
- 既存ドロップテーブルとの確率共通化
- 採取ログとクラフト導線の UI 強化
