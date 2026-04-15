# GATHERING_RESPAWN_VERTICAL_SLICE

## 概要

採取ポイントの再利用ループを、既存の Playable Slice に最小差分で追加する。
目的は「時間経過システム」ではなく、宿屋・帰還を契機に採取素材を再収集し、クラフト/納品導線を継続可能にすること。

## 今回の対応範囲

- マスターデータ拡張（`data/master/gathering_nodes.sample.json`）
  - `respawn_rule`: `none` / `on_rest` / `on_return_to_hub`
  - `respawn_description`: CLI表示用の補助説明
- ランタイム状態
  - 既存の `gathered_node_ids` を継続利用
  - リポップ時は対象 node_id を `gathered_node_ids` から除外
- トリガー連携
  - 宿屋宿泊成功時: `on_rest`
  - 拠点帰還時（移動または戦闘帰還）: `on_return_to_hub`
- Save/Load
  - 既存 `meta.gathering_state.gathered_node_ids` を継続利用
  - ロード時に未知 node_id を検知して失敗させる

## 接続ポイント

- Gathering
  - 採取可否判定は既存 `GatheringService` を維持
  - リポップ判定/更新は `GatheringRespawnService` として分離
- Inn
  - 宿泊ロジック本体は `InnService` の責務を維持
  - `PlayableSliceApplication` 側で宿泊成功後にリポップトリガーを適用
- Location / Return
  - 拠点への移動成功時にリポップトリガーを適用
  - 戦闘後の自動帰還時にも同トリガーを適用
- Crafting / Turn-in Quest
  - 再採取で素材再取得が可能になり、既存のクラフト/納品導線を継続利用可能

## 実行方法

```bash
python -m unittest tests.test_gathering_slice
python -m unittest tests.test_playable_slice
python -m unittest
python -m game.app.cli.run_game_slice
```

CLIログでは以下を確認できる:

- `gathering_respawned:on_rest:*`
- `gathering_respawned:on_return_to_hub:*`
- `gather_node:*:respawn_rule=...`

## スコープ外

- 時刻/日付ベースの自動リポップ
- ロケーション別クールダウン日数
- 採取ツール/採取ランク/天候条件
- 一括日次リセットUI

## 次の拡張ポイント

- `respawn_group_id` を使ったグループ単位のリポップ
- `meta` に最終リポップ時点を保持し、時間経過判定へ拡張
- 採取ランク・装備パッシブ連動（採取成功率/追加ドロップ）
