# EQUIPMENT SET BONUS VERTICAL SLICE

## 概要
- 装備単体性能に加えて、シリーズ装備を組み合わせた段階式ボーナスを最小実装した。
- セット定義は `data/master/equipment_sets.sample.json` に分離し、実行時は現在の装備状態から都度評価する。
- 既存の Equipment / Crafting / Workshop / Miniboss / Save / Playable Slice の導線を再利用し、責務を跨がない形で統合した。

## 今回の実装範囲

### セット定義（master data）
- `data/master/equipment_sets.sample.json` を追加。
- 最小フィールド:
  - `set_id`
  - `name`
  - `description`
  - `member_equipment_ids`
  - `set_bonuses[]`
    - `required_piece_count`
    - `bonus_type`
    - `parameters`
    - `bonus_description`
- サンプルセット `set.tidebreaker.assault`:
  - 2部位: `stat_bonus`（ATK/DEF上昇）
  - 3部位: `stat_bonus`（追加ATK/SPD）
  - 3部位: `status_resistance`（毒耐性）

### 評価基盤
- `EquipmentSetService` を追加し、以下を担当。
  - 現在装備からセット成立数を計算
  - 段階式ボーナスの解決
  - 有効ボーナス一覧の取得
- `AppMasterDataRepository.load_equipment_sets(...)` で定義を読み込み、最低限バリデーションを実施。
  - 未知装備ID検知
  - `required_piece_count` の範囲検証
  - `bonus_type` 検証

### 装備性能反映
- `EquipmentService` にセットボーナス解決フックを追加。
  - 最終ステータス計算 (`resolve_final_stats`) にセット `stat_bonus` を加算。
  - `passive_summary` にセット由来パッシブを統合。
- 既存の装備個別パッシブ・強化ボーナスと共存可能。

### Playable Slice 接続
- `PlayableSliceApplication` で装備変更時にセットボーナス再評価。
  - `set_bonus_activated:*`
  - `set_bonus_deactivated:*`
- ステータス表示に発動中セット段階を追加。
  - `active_set_bonuses=[...]`
- 工房導線（会話時ログ）にセット進捗ヒントを追加。
  - 未成立
  - 2/3部位達成
  - 全段階発動中

### Crafting / Workshop / Miniboss 接続
- 3部位成立のため、アクセサリ `equip.accessory.tidecrest_ring` を追加。
- 上位レシピ `recipe.craft.tidecrest_ring` を追加（工房ランク3 / レシピ発見条件あり）。
- 既存の `recipe.craft.tidebreaker_harness`（ミニボス素材 `guardian_core` 使用）と組み合わせることで、
  上位工房ループ内でセット収集の意味が生まれる構成にした。

### Save / Load 方針
- セット効果そのものは保存しない。
- 既存の装備状態を保存し、Load 後に再評価して復元する。
- save contract の追加キーは不要（既存互換を維持）。

## 実行方法
- 全体: `python -m unittest`
- セット効果関連: `python -m unittest tests.test_equipment_set_bonus_slice`
- 手動確認: `python -m game.app.cli.run_game_slice`

## 今回のスコープ外
- 複数セット同時発動の優先度UI
- 条件付き変化セット
- セット専用GUI管理画面
- セット効果の高度な最適化表示

## 次の拡張ポイント
- 複数パーティメンバーでのセット成立判定（全体/個別の切替）
- セット効果の `skill_modifier` 実動作（既存スキル計算との接続）
- 工房NPC会話をデータ駆動の段階分岐へ移管
