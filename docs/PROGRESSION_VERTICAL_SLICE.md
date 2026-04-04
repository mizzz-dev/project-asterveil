# Progression Vertical Slice (報酬・所持品・成長)

## 概要

Playable Slice に、戦闘/クエストの結果をプレイヤー状態へ反映する最小ループを追加した。

- 戦闘勝利時: EXP / Gold / Item を付与
- クエスト完了時: EXP / Gold / Item を付与
- 成長: パーティメンバーへ EXP 加算、レベルアップ、最小ステータス上昇
- 永続化: Save / Load で成長状態と所持品を保持

## 実装範囲

### 報酬基盤

- `RewardBundle` / `BattleReward` / `RewardApplicationService` を追加
- 戦闘報酬は `data/master/reward_tables.sample.json` から読込
- クエスト報酬は既存 quest 定義に `reward.items` を追加して拡張

### 成長基盤

- `ProgressionService` を追加
  - `required_exp_for_level(level)` で最小式の必要経験値
  - `grant_exp()` で EXP 加算とレベルアップ処理
  - レベルアップ時: `max_hp/max_sp/atk/defense/spd` を上昇

### 所持品/通貨

- `inventory_state = { gold, items }` を Playable Slice の実行時状態として管理
- `items` は `item_id -> count` の最小個数管理
- `data/master/items.sample.json` を追加し、報酬参照を検証

## Save / Load 接続

- `PartyMemberState` に progression 用フィールドを追加
  - `current_exp`, `next_level_exp`
  - `max_hp`, `max_sp`, `atk`, `defense`, `spd`
- 既存 `inventory_state` と合わせて JSON へ保存/復元
- v1 契約は維持し、追加フィールドは後方互換の既定値で復元可能

## 実行方法

```bash
python -m game.app.cli.run_game_slice
python -m unittest
```

## 今回のスコープ外

- 装備変更によるステータス再計算
- ショップ/売買
- アイテム使用処理
- 複数ドロップテーブルとレアドロップ制御

## 次の拡張ポイント

- キャラクターごとの成長曲線 (`growth_curve_id`) への接続
- Battle 実行時に save 側の成長ステータスを反映
- クエスト報酬の複数テーブル化（難易度・周回補正）
