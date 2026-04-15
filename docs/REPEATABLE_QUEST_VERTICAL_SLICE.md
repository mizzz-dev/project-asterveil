# REPEATABLE QUEST VERTICAL SLICE

## 目的

採取・納品・討伐を同一セーブ内で周回できる最小導線として、
一部クエストの**再掲待ち → 再受注可能 → 再受注**を追加する。

## 今回の対応範囲

- Quest master data に以下を追加
  - `repeatable`
  - `repeat_reset_rule`（`on_rest` / `on_return_to_hub` / `manual_reaccept`）
  - `repeat_category`（任意）
  - `reaccept_message`（任意）
- Quest runtime state に `repeat_ready` を追加
- Quest Board status に以下を追加
  - `repost_waiting`（再掲待ち）
  - `reacceptable`（再受注可能）
- 宿屋宿泊 (`on_rest`) / 拠点帰還 (`on_return_to_hub`) を再掲トリガーとして接続
- SaveData v1 の quest state に `repeat_ready` を追加（後方互換の optional 読み込み）

## マスターデータ例

- `quest.ch01.herb_supply_turn_in`
  - `repeatable=true`
  - `repeat_reset_rule=on_rest`
  - 採取→納品周回向け
- `quest.ch01.harbor_cleanup`
  - `repeatable=true`
  - `repeat_reset_rule=on_return_to_hub`
  - 討伐→帰還周回向け

## 状態遷移（最小）

1. 受注可能 (`available`) から受注
2. 進行中 (`in_progress`) → 報告可能 (`ready_to_complete`) → 完了 (`completed`)
3. repeatable の場合はボード上で `repost_waiting`
4. トリガー一致で `repeat_ready=true` になり `reacceptable`
5. 再受注で objective progress / objective item progress を初期化

## 既存機能との接続

- Quest Board
  - `status=repost_waiting` と `status=reacceptable` を表示
  - `reacceptable` のとき `accept_quest` が再受注処理へ分岐
- Inn
  - 宿泊成功時に `on_rest` トリガーで repeatable quest の再掲判定
- Location / Hunt
  - 拠点帰還時に `on_return_to_hub` トリガーで再掲判定
- Save / Load
  - `repeat_ready` を保存・復元

## 実行方法

- `python -m unittest tests.test_quest_slice`
- `python -m unittest tests.test_playable_slice`
- `python -m unittest tests.test_save_slice`

## スコープ外

- 日次・週次更新
- 掲示板自動入れ替え
- ランダム依頼生成
- 同時複数インスタンス受注

## 次の拡張ポイント

- `repeat_reset_rule` を複数トリガー対応（AND/OR 条件）に拡張
- `repeat_category` に基づく掲示板フィルタ/表示強化
- 再受注回数や最終再掲時刻を `quest_runtime_meta` として保存
