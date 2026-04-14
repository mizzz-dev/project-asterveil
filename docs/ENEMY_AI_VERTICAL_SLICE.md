# ENEMY AI VERTICAL SLICE (最小行動選択)

## 概要

本スライスでは、敵の行動を「通常攻撃固定」から、マスターデータ定義に基づく最小AIへ拡張した。

- `data/master/enemy_ai.sample.json` から AI プロファイルを読み込み
- 敵ごとに `enemies.sample.json` の `ai_profile_id` でプロファイルを紐付け
- `priority` と `conditions` により行動ルールを評価
- `target_rule` により単体対象を自動選択
- 条件不一致時は通常攻撃へフォールバック
- 戦闘ログに `enemy_ai:selected_rule=...` を出力

## 対応した最小要件

- 行動タイプ
  - `normal_attack`
  - `skill`
- 条件
  - `self_hp_below_ratio`
  - `enemy_has_no_effect`
  - `ally_needs_heal`
  - `ally_count_alive_at_least`
- ターゲットルール
  - `lowest_hp_enemy`
  - `random_enemy`
  - `self`
  - `lowest_hp_ally`
  - （全体スキル時）`all_enemies` / `all_allies` は `target_id=None` 扱い

## 既存機能との接続

- **Status Effect**:
  - `enemy_has_no_effect` により毒・防御低下の重複付与を抑制。
- **Support Skill**:
  - `skill.enemy.shadow_mend` で低HP味方への回復を実行。
- **Playable Slice / Quest / Battle**:
  - `build_battle_executor` 経由の通常バトルでも敵AIを使用。
- **Save / Load**:
  - AI定義はマスターデータでありセーブ対象外。
  - 戦闘中の判断状態も保存対象外（従来どおり戦闘後の party/quest/inventory 等を保存）。

## 実行方法

```bash
python -m unittest tests.test_enemy_ai_slice -v
python -m unittest
python -m game.battle.cli.run_battle
```

## スコープ外

- ボス専用フェーズ遷移
- ヘイトシステム
- 重み付き確率選択
- 複数ターン先読み
- 戦闘途中保存

## 次の拡張ポイント

1. ルール条件に `turn_count` / `ally_dead_count` / `has_skill_available` を追加
2. `priority` 同値時のランダム分岐（現在は定義順）
3. 敵ロール（attacker/debuffer/healer）単位の共通テンプレート化
4. ボス向け `phase` 条件と専用スクリプトフックの追加
