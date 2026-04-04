# Dialogue / Location Event Vertical Slice

## 概要

本スライスでは、データ駆動の最小構成として以下を追加した。

- NPC会話定義 (`data/master/npcs.sample.json`, `data/master/dialogues.sample.json`)
- ロケーション入場イベント定義 (`data/master/location_events.sample.json`)
- 条件評価と解決を行う会話/イベントサービス
- Playable Slice への `NPCと話す` / `ロケーション入場イベント` の統合
- イベント実行済み状態の Save/Load 永続化

## 対応した会話条件

- `required_flags`
- `excluded_flags`
- `required_quest_status`
- `required_location_id`
- 優先度 (`priority`) による解決順
- 不一致時のフォールバック会話

## ロケーション入場イベントでできること（最小）

- `trigger_type = on_enter_location`
- 条件一致時にイベントを実行
- 実行アクション
  - `start_battle`
  - `set_flag`
  - `accept_quest`
- `repeatable: false` の場合は再発防止

## 既存スライスとの接続

- Quest: `QuestState` / `QuestStatus` を参照して会話・イベント条件を判定
- Battle: 入場イベントから固定戦闘を起動し、勝利時の報酬とクエスト進行更新を適用
- Location: `travel_to` 成功後に `on_enter_location` イベント解決を実行
- Save: `meta.event_state.completed_location_event_ids` に完了イベントIDを保存
- Playable: `NPCと話す` をメニュー追加し、現在地NPC一覧から会話可能

## 実行方法

- CLI 起動: `python -m game.app.cli.run_game_slice`
- 進行例:
  1. クエスト受注
  2. 干潟へ移動
  3. 入場イベント発火（固定戦闘 + フラグ更新）
  4. 町へ戻ってNPC会話変化を確認
  5. Save/Load 後にイベント再発しないことを確認

## 今回のスコープ外

- 選択肢分岐会話
- 複数イベント連鎖のスクリプト制御
- カットシーン演出
- 会話ログ履歴管理

## 次の拡張ポイント

- `actions` に `complete_quest` / `grant_reward` / `teleport` を追加
- 会話に `talk_once` や `cooldown` 条件を追加
- NPC配置をロケーションごとの複数スポット管理へ拡張
- イベントチェイン（開始条件にイベント完了IDを利用）
