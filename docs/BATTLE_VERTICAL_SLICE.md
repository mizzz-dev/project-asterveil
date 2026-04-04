# BATTLE VERTICAL SLICE (最小戦闘コア)

## 概要

Vertical Slice 向けに、データ駆動で動く最小戦闘コアを実装しました。

- マスターデータ (`data/master/*.sample.json`) からキャラクター/敵/スキルを読込
- プレイヤーvs敵のターン制バトルを進行
- `attack` と `skill`（`skill.striker.flare_slash`）を実行
- HP更新、戦闘不能、勝敗判定を実装
- Domain / Application / Infrastructure を分離

## スコープ内

- 単体対象行動
- SPD依存の行動順
- 単純ダメージ計算 (`atk * power - def`, 最低1)
- 自動コマンド選択（SPがあればスキル優先）

## スコープ外（今回あえて未実装）

- CTBのWeight反映
- 属性相性、弱点、ブレイク、状態異常
- マルチターゲット、バフ/デバフ、クリティカル
- UI/HUD統合
- ネットワーク同期

## 実行方法

### 1) サンプル戦闘を実行

```bash
python -m game.battle.cli.run_battle
```

### 2) テスト実行

```bash
python -m unittest tests.test_battle_core -v
```

## 次の拡張ポイント

1. `ActionCommand` を入力ソース別（Player/AI/Remote）に切替可能化
2. `SkillDefinition.effect_blocks` の複数効果対応
3. `BattleState` にWT/CTBゲージを追加し、`weight` を行動順へ反映
4. AIプロファイル（`skill_rotation_id`）をRepository経由で接続
