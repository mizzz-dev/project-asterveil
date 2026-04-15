# MULTI_STAGE_QUEST_VERTICAL_SLICE

## 概要
- 本スライスでは、1クエスト内で objective を順番に進める最小実装を追加した。
- 対応 objective type は `gather_items` / `discover_recipe` / `craft_item` / `turn_in_items`。
- 既存の `kill_enemy` / 単段 objective クエストとの互換性を維持した。

## 今回追加した最小ループ
- 対象クエスト: `quest.ch01.workshop_supply_chain`
- 段階:
  1. 素材採取（解毒草 + 鉄片）
  2. レシピ発見（工房 NPC 会話）
  3. クラフト（潮香トニック調合）
  4. 納品（完成品 turn-in）

## 実装ポイント
- `QuestProgressService` に active objective 判定と段階遷移を追加。
- objective 完了時に `objective_completed` / `next_objective_unlocked` / `quest_ready_to_report` を出力。
- `PlayableSliceApplication` で gather / recipe discovery / craft / turn-in 完了時に quest 進捗を更新。
- objective 段階を表す world flag を `flag.quest.objective.active:*` / `flag.quest.objective.completed:*` として反映し、dialogue 側はこれを参照して会話を分岐。

## Save/Load 方針
- 保存は既存 `objective_progress` / `objective_item_progress` を再利用。
- active objective は保存専用フィールドを追加せず、ロード後に `objective_progress` から再計算。
- これにより save contract v1 の互換を維持する。

## 実行方法
- 全体テスト: `python -m unittest`
- 重点テスト:
  - `python -m unittest tests.test_quest_slice`
  - `python -m unittest tests.test_playable_slice`
  - `python -m unittest tests.test_save_slice`

## 今回のスコープ外
- 並列 objective
- 分岐 objective
- 代替達成条件
- クラフト品質条件
- 章またぎ依頼

## 次の拡張ポイント
- objective 単位の失敗条件 / 制限時間
- objective 遷移トリガーのデータ駆動化（現在は type ごとの最小実装）
- objective 単位報酬や中間報酬
