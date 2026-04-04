# QUEST BOARD Vertical Slice（最小実装）

## 概要
本スライスでは、拠点メニューからクエストボードを開き、複数クエストの状態を確認・受注・進行・報告できる最小ループを追加した。

対応状態:
- `locked`（未解放）
- `available`（受注可能）
- `in_progress`（進行中）
- `ready_to_complete`（報告可能）
- `completed`（完了）

## 解放条件
`quests.sample.json` の `availability` で最小条件を表現する。
- `required_quest_ids`: 前提クエスト完了条件
- `required_flags`: フラグ条件
- `min_level`: 最低レベル条件

今回サンプルでは、以下を実装済み:
- 連鎖解放: `quest.ch01.harbor_cleanup` は `quest.ch01.missing_port_record` 完了後に解放
- レベル + フラグ解放: `quest.ch01.rookie_level_trial` は `flag.game.new_game_started` かつ `level >= 8`

## Playable Slice接続
- 拠点メニューに `クエストボードを見る` を追加
- ボード表示で `can_accept=True` のクエストのみ受注操作可能
- 受注上限は同時2件（`QuestBoardService.max_active_quests=2`）
- 討伐は進行中クエスト1件を対象として戦闘を実行
- 報告は `ready_to_complete` のクエストを完了し、既存Rewardサービスで報酬適用

## Save接続
既存 `quest_state` 契約を再利用。
- quest_idごとの `status`
- objective進捗配列
- `reward_claimed`

追加の保存契約変更は不要。

## 実行
- CLI起動: `python -m game.app.cli.run_game_slice`
- 拠点メニューで `クエストボードを見る` を選択
- 受注 → 討伐 → 報告
- `セーブする` / `ロードする` で状態保持を確認

## スコープ外
- デイリー更新
- 受注破棄
- 複雑なAND/OR条件
- 時限クエスト
- 章を跨ぐ進行演出

## 次の拡張ポイント
- クエストカテゴリ別タブ表示
- 依頼人/NPC別表示と報告先導線
- objective種別の追加（収集・会話・探索）
- 複数進行中クエストの対象戦闘選択UI
