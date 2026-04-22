# WORKSHOP STORY VERTICAL SLICE

## 概要

- 工房ランクの進行に、工房主イェルドと工房助手ルカの小規模ストーリー導線を追加。
- `data/master/workshop_story.sample.json` で段階条件と解放報酬を定義し、ランタイム進行は `WorkshopStoryState` で管理。
- ランク2時点で上位探索依頼を案内し、ランク3到達後の納品達成で上位レシピを解放する最小ループを構成。

## 接続ポイント

- Workshop Rank: `workshop_progress_state.level` を段階判定に利用。
- Dialogue: 工房NPC会話 (`talk_to_npc`) 終了時に段階評価を行い、`workshop_story_advanced:*` を出力。
- Quest: ストーリー段階報酬で `quest.ch01.workshop_rank3_expedition` を解放。
- Advanced Crafting: 上位依頼達成後に `recipe.craft.workshop_oceanic_polish` を解放。
- Save: `meta.workshop_story_state` に既読段階/解放状態を保存。
- Playable Slice: 既存CLI導線を維持したまま工房NPC会話で進行が自然に更新される。

## 実行方法

- 全体テスト:
  - `python -m unittest`
- 工房ストーリー関連のみ:
  - `python -m unittest tests.test_workshop_story_slice`

## スコープ外

- 工房NPCごとの長編分岐シナリオ
- 工房以外施設への同等ストーリー展開
- 演出強化（GUI/ボイス/カットシーン）

## 次の自然な拡張

- `unlock_rewards` の `location_ids` / `field_event_ids` を使った探索段階の追加。
- 工房助手専用の repeatable 依頼カテゴリと工房ランク4以降の段階定義追加。
