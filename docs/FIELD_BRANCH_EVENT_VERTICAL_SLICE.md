# Field Branch Event Vertical Slice

## 今回の実装

- `data/master/location_events_branching.sample.json` を追加し、ロケーション探索中に手動実行できる分岐イベント定義を導入。
- `FieldEventDefinition / FieldEventChoice / FieldEventOutcome` 相当のモデルと、マスターデータ読み込みリポジトリ、実行サービスを追加。
- Playable Slice に「探索イベントを調べる」導線を追加し、イベント選択 → 選択肢選択 → 結果反映を CLI で実行可能にした。
- `meta.event_state` に一度きりイベント実行済みIDと選択履歴を保存し、Save/Load 後に復元。

## 対応した分岐と結果

- 2択イベントを2件追加（`event.field.tidal_flats.drift_supply`, `event.field.tidal_flats.toxic_mushroom`）。
- 安全選択と危険選択の差分（安全: 小報酬、危険: 戦闘 + 報酬）。
- イベント結果として以下を実装。
  - `show_message`
  - `set_flag`
  - `grant_items`
  - `start_battle`
  - `apply_effect_to_party`
  - `unlock_treasure_node`（フラグ経由で探索報酬ノードを解放）

## 既存スライスとの接続

- **Inventory**: `grant_items` で既存 inventory 状態へ加算。
- **Battle**: `start_battle` で既存 battle executor を呼び出し。
- **Status Effect**: `apply_effect_to_party` で既存 `PartyActiveEffectState` を付与。
- **Dialogue**: `set_flag` の結果を会話条件に利用し、会話差分が発生。
- **Treasure**: `unlock_treasure_node` でフラグを立て、`required_flags` により開封可否を制御。
- **Save**: `meta.event_state.completed_field_event_ids` / `field_event_choice_history` を保存・復元。

## 実行方法

```bash
python -m game.app.cli.run_game_slice
```

進行例:
1. New Game
2. クエスト受注後に `潮だまりの干潟` へ移動
3. `探索イベントを調べる` でイベントを選択
4. 選択肢を選び、`field_event_resolved:*` / `field_choice_selected:*` を確認
5. セーブ→ロードでイベント実行済み状態を確認

## 今回のスコープ外

- ランダム抽選によるイベント発生率制御
- 時間経過や章進行によるイベント群の差し替え
- 複数段チェインの専用スクリプト実行

## 次の拡張ポイント

- `required_quest_status` や `cooldown` 条件をフィールドイベント定義に追加
- イベント結果の履歴（複数回分）保存
- ロケーション探索の「推奨イベント」提示やヒント導線
