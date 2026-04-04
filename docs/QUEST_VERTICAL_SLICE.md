# QUEST VERTICAL SLICE (会話イベント + クエスト最小進行)

## 概要

Vertical Slice 向けに、会話イベントからクエスト受注と戦闘を接続する最小進行ループを実装しました。

- `data/master/events.sample.json` から会話イベントを読込
- `data/master/quests.sample.json` からクエスト定義を読込
- `未受注 → 進行中 → 達成可能 → 完了` の状態遷移を実装
- イベントアクション `start_battle` から既存戦闘コアを起動
- 戦闘勝敗でクエスト進行を更新
- 完了時に報酬情報と完了フラグを反映

## スコープ内

- 直列ステップ型イベント（分岐なし）
- 討伐目標 `kill_enemy` 1種類
- クエスト受注 / 進行更新 / 完了
- CLIでの一連確認（会話→受注→戦闘→報告完了）

## スコープ外（今回あえて未実装）

- 選択肢分岐会話
- 複数章をまたぐシナリオ制御
- セーブデータ完全統合
- GUI会話/クエストUI
- 複合報酬経済や複数目標同時管理

## 実行方法

### 1) クエスト Vertical Slice ランナー

```bash
python -m game.quest.cli.run_quest_slice
```

### 2) テスト

```bash
python -m unittest tests.test_quest_slice -v
python -m unittest tests.test_battle_core tests.test_quest_slice -v
```

## 既存戦闘コアとの接続

- `QuestSliceSession` の `start_battle` アクションで `battle_executor` を呼び出す
- `battle_executor` は `BattleSession` を起動して勝敗を返す
- 勝利時のみ `BattleResult.defeated_enemy_ids` をクエスト進行へ反映
- 敗北時は `IN_PROGRESS` のまま保持し、再挑戦可能

## 次の拡張ポイント

1. イベント条件分岐（フラグ条件、クエスト状態条件）
2. objective種別追加（収集、会話、地点到達）
3. セーブ契約 `quest_state / world_flags` への統合
4. encounter定義をマスターデータ化して `ENCOUNTER_TO_ENEMY_ID` のハードコード除去
