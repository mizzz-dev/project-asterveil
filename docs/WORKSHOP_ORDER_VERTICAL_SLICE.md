# WORKSHOP ORDER VERTICAL SLICE

## 目的
- 工房を repeatable な納品依頼とランク成長のハブとして扱う最小ループを追加する。
- 既存 Quest / Turn-in / Crafting / Save / Playable 導線を流用し、重複実装を避ける。

## 今回の実装範囲
- `data/master/workshop_orders.sample.json` を追加。
  - 工房依頼定義（order_id, repeatable, repeat_reset_rule, required_turn_in_items, workshop_progress_value）
  - 工房ランク定義（required_progress, unlock_recipe_ids）
- `quest_category=workshop_order` の repeatable 納品依頼を2件追加。
  - 素材納品: `quest.ch01.workshop_iron_delivery`
  - 完成品納品: `quest.ch01.workshop_tonic_order`
- `WorkshopProgressService` により、工房依頼完了時に進行値を加算しランクアップ判定。
- ランクアップ時に `recipe_unlocked_by_workshop_rank:*` を出力し、上位レシピを解放。
- セーブ契約の `meta.workshop_state` へ工房ランク状態を保存/復元。

## 接続方針

### Quest / Repeatable / Turn-in
- 工房依頼自体は既存 `quests.sample.json` の repeatable クエストとして定義。
- 受注/納品/再受注/リセットルールは既存 `QuestProgressService` を再利用。
- 工房進行値だけを `WorkshopProgressService` で別責務として加算。

### Crafting / Recipe Discovery
- 「レシピを知っている（unlock/discovery）」と「工房ランクで作成可能」を分離。
- `craft_recipe` は既存の解放条件に加え、工房ランク解放判定も必要にした。
- `recipe.craft.workshop_guard_oil` は rank1 では作成不可、rank2 到達で作成可能。

### Dialogue / Playable
- 工房NPC会話に rank1/rank2 の差分行を追加。
- 工房NPC会話時に以下ログを表示。
  - 現在ランク
  - 次ランクまで残量
  - 工房依頼の進行状況
  - 工房ランク由来の解放レシピ一覧

### Save / Load
- `meta.workshop_state` に以下を保持。
  - `rank`
  - `progress`
  - `unlocked_recipe_ids`
  - `order_completion_counts`
  - `applied_completion_markers`

## 実行方法
- `python -m unittest tests.test_workshop_order_slice`
- `python -m unittest tests.test_playable_slice tests.test_quest_slice`

## 今回のスコープ外
- 工房専用通貨
- 工房スタッフ人数管理
- 複数工房 / 設備スロット
- 完成版の工房経営UI

## 次の拡張ポイント
- 依頼カテゴリ別ポイント（採取/討伐/完成品）
- 日次更新型の工房依頼ローテーション
- ランクごとの工房イベントチェーン
