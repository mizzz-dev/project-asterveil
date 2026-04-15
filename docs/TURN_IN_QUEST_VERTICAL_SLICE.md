# TURN_IN_QUEST_VERTICAL_SLICE

## 概要
- 納品クエスト（`objective_type: turn_in_items`）の最小実装を追加。
- Quest 定義（master data）と、納品進捗（runtime/save data）を分離。
- 採取素材・戦利品素材を `inventory` 経由で納品可能。

## 今回の対応範囲
- `data/master/quests.sample.json`
  - `turn_in_items` objective を持つ納品クエストを2件追加。
  - `required_items[].item_id / quantity` と `reporting_npc_id` を利用。
- Quest進行
  - 納品可否判定（不足時失敗）
  - 在庫消費
  - objective進捗更新
  - 必要数達成で `ready_to_complete`
- Dialogue/NPC導線
  - 報告NPC会話から納品処理を実行。
  - 不足時は `turn_in_failed:insufficient_items`、成功時は `turn_in_success:*` を返す。
- Save/Load
  - `objective_item_progress` を保存・復元（v1互換を保つ追加フィールド）。

## 接続ポイント
- Inventory: `inventory_state["items"]` を納品元として使用。
- Gathering: `node.herb.astel_backyard_01` 由来アイテムを納品可能。
- Loot/Battle Reward: `item.material.memory_shard` を納品可能。
- Crafting: `inventory` 基盤を共通利用するため、クラフト産アイテムも同じ導線で拡張可能。
- Playable Slice: `talk_npc` の選択効果として `turn_in_quest` を追加。

## 実行方法
- 全テスト: `python -m unittest`
- 納品関連のみ:
  - `python -m unittest tests.test_quest_slice`
  - `python -m unittest tests.test_playable_slice`

## スコープ外（今回未実装）
- 部分納品UIの専用表示改善
- 複数段階納品チェーン
- 依頼カテゴリの高度な絞り込み
- 納品専用NPC画面の完成版

## 次の拡張候補
- `allow_partial_turn_in=true` クエストのUI導線追加。
- 複数 `required_items` objective の段階表示（アイテム別進捗一覧）。
- クラフト品納品クエストの正式サンプル追加。
