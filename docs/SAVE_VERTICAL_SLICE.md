# SAVE VERTICAL SLICE

## 1. 目的

Vertical Slice で必要な最小の永続化として、次を成立させる。

- クエスト進行状態の保存 / 復元
- ワールドフラグの保存 / 復元
- パーティの最小実行時状態（HP/SP/生存）の保存 / 復元
- 受注後に保存し、再ロードして報告イベントを継続できること

## 2. スコープ

### 保存対象

- `save_version`
- `player_profile`（難易度・プレイ時間・最終保存時刻）
- `party_state.members`
  - `character_id`
  - `level`
  - `current_hp`
  - `current_sp`
  - `alive`
  - `equipped`
  - `unlocked_skill_ids`
- `quest_state`
  - `status`
  - `objective_progress`（クエスト定義順の配列）
  - `reward_claimed`
- `world_flags`
- `progression.last_event_id`
- `inventory_state`
- `meta`

### スコープ外

- 暗号化
- クラウドセーブ
- 複数スロットの完成版管理
- UI統合
- マイグレーション完成版

## 3. レイヤー責務

- `game/save/domain/entities.py`
  - 保存契約モデル（`SaveData`）
  - バージョン検証（v1固定）
  - 最低限の必須項目検証
- `game/save/application/session.py`
  - Quest Session ↔ SaveData の変換
  - objective進捗の順序変換（dict ↔ list）
- `game/save/infrastructure/repository.py`
  - JSONファイル保存
  - テスト向けインメモリ保存

## 4. 既存 Quest / Battle との接続

- Questは `QuestSliceSession` の `quest_states` と `world_flags` を保存対象にする。
- Battle結果で更新されたクエスト進行（`READY_TO_COMPLETE` など）をそのまま保存する。
- ロード時に `QuestSliceSession` へ状態を戻し、続きの `event.ch01.port_report` を実行できる。

## 5. 実行方法

```bash
python -m game.save.cli.run_save_slice
```

確認できる流れ:

1. 受注イベント実行（戦闘含む）
2. `tmp/save_slot_01.json` へ保存
3. ロード
4. 報告イベント継続
5. 再保存

## 6. 将来拡張時の注意

- `quest_state.objective_progress` はクエスト定義の objective 順序に依存する。
- objective追加 / 並び替え時は `save_version` を上げて移行処理を追加する。
- `world_flags` は真偽値以外（章番号など）を許容しているため、型制約強化時は互換性を確認する。
