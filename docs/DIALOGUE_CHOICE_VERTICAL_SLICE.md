# Dialogue Choice / Flag Branching Vertical Slice

## 概要

本スライスでは、既存の Dialogue / Location Event 基盤に対して、
「会話中の選択によってフラグと後続会話が変化する」最小ループを追加した。

- マスターデータで会話ステップと選択肢を定義
- 選択肢の表示条件（required / excluded flags）を評価
- 選択で `world_flags` を更新
- 選択効果として `accept_quest` / `set_flag` / `start_battle` / `end_dialogue` を実行可能
- 選択結果は既存 Save/Load（`world_flags`）で永続化

## 追加したデータ定義（最小）

`data/master/dialogues.sample.json` の各エントリに、互換を壊さない拡張として `steps` を追加できる。

- `steps[*].step_id`
- `steps[*].speaker`
- `steps[*].line` または `steps[*].lines`
- `steps[*].choices[]`
  - `choice_id`
  - `text`
  - `next_step_id`
  - `set_flags`
  - `required_flags`（任意）
  - `excluded_flags`（任意）
  - `effects`（任意）

## Playable Slice 接続

- `NPCと話す` 導線で、選択肢付き会話の場合は CLI で選択可能
- 選択後に次ステップの台詞を即時表示
- `flag_set:*` / `choice_selected:*` をログ表示
- 同一 NPC の後続会話と、別 NPC（見張り兵）の台詞が分岐

## Quest / Location / Save との接続

- 選択肢効果 `accept_quest` により既存クエスト受注処理を再利用
- フラグ分岐で Guard の台詞が変化
- 保存契約は既存の `world_flags` で表現可能なため変更なし

## 実行方法

- `python -m game.app.cli.run_game_slice`
- New Game 開始後、`NPCと話す` で「港長オルド」を選択
- 「引き受ける / 今はやめておく」を選択
- 続けて「見張り兵ミナ」に話しかけると台詞分岐を確認できる
- Save → Load 後も分岐結果が維持される

## 今回のスコープ外

- 多段ツリーの大量分岐
- 好感度・章進行と結びついた複合条件
- 分岐チャートの可視化
- GUI 選択肢 UI

## 次の拡張ポイント

- `required_quest_status` を choice 側にも拡張
- 選択肢の one-shot 制御（選択済み履歴）
- 分岐先イベント（location event / quest event）のデータ接続拡張
