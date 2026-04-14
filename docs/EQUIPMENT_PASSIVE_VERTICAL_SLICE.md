# EQUIPMENT PASSIVE VERTICAL SLICE

## 目的
- 装備ごとのパッシブ効果をマスターデータで定義し、戦闘中の挙動差として体感できる最小ループを成立させる。
- 責務分離として、`equipment.sample.json` は静的定義のみを保持し、実行時は装備状態から都度パッシブを解決する。

## 今回の実装範囲
- `data/master/equipment.sample.json` に `passive_effects` を追加。
- 対応した `passive_type`（最小）
  - `status_resistance`
  - `heal_bonus`
  - `battle_start_effect`
  - （拡張フック）`sp_cost_modifier` / `stat_bonus`
- `EquipmentPassiveService` を追加し、以下を分離。
  - 装備状態からパッシブ一覧を解決
  - 戦闘開始時効果の適用
  - 状態異常付与時の耐性判定
  - 回復量補正/消費SP補正の計算

## 接続ポイント
### Battle
- `BattleSession.create(...)` で装備状態を受け取り、戦闘単位で `UnitPassiveContext` を生成。
- `apply_action(...)` で、
  - 状態異常付与前に耐性判定
  - 回復スキル時の回復量補正
  - （必要時）SP消費補正
  を反映。

### Equipment / Shop / Playable Slice
- 装備定義読込時にパッシブを検証して保持。
- ショップにパッシブ付き装備を追加し、購入→装備変更→戦闘反映の導線を既存フローへ接続。
- ステータス/装備表示で `passives=[...]` を表示。

### Save / Load
- パッシブ定義は保存しない。
- 既存の装備状態（`party_state.members[].equipped`）を保存し、ロード後に再解決する。
- save contract のキー追加は不要（互換維持）。

## 実行方法
- 全体テスト: `python -m unittest`
- 装備パッシブ関連のみ: `python -m unittest tests.test_equipment_passive_slice tests.test_battle_core`
- 手動確認: `python -m game.app.cli.run_game_slice`

## 今回のスコープ外
- セット効果
- 複数パッシブの高度な相互作用
- 発動率付き条件パッシブ
- UI上での詳細比較表示
- 完成版耐性計算（今回の耐性はON/OFF）

## 次の拡張ポイント
- `status_resistance` を確率/倍率耐性へ拡張。
- `battle_start_effect` の対象拡張（味方全体/条件付き）。
- `stat_bonus` の恒常反映を戦闘外ステータス計算へ統合。
- ログ分類（`passive_triggered:*`）の可視化強化。
