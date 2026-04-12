# SUPPORT SKILL VERTICAL SLICE

## 概要

本スライスでは、戦闘中の **味方対象スキル / 回復 / 支援** を最小実装した。

- 味方単体回復 (`single_ally` + `heal`)
- 味方単体状態異常回復 (`single_ally` + `cure_effect`)
- 味方全体回復 (`all_allies` + `heal`)
- 既存の SP 消費・習得スキル制御・状態異常基盤・セーブ契約と整合

## 実装内容

### スキル定義の拡張
`data/master/skills.sample.json` で以下を利用する。

- `target_scope`: `single_ally`, `all_allies`, `single_enemy`, `all_enemies`
- `effect_kind`: `damage`, `heal`, `apply_effect`, `cure_effect`
- `heal_power`: 回復量係数
- `remove_effect_ids`: 回復対象の状態異常ID

追加スキル:
- `skill.striker.first_aid` (味方単体回復)
- `skill.striker.cleanse` (味方単体毒回復)
- `skill.striker.warm_prayer` (味方全体小回復)

### バトル処理
- `single_ally` / `all_allies` の対象解決
- 戦闘不能対象の最小判定（味方単体への回復は不可）
- 回復上限 (`max_hp` を超えない)
- 状態異常回復 (`remove_effect_ids`)
- ログ出力:
  - `heal_applied`
  - `effect_applied`
  - `effect_cured`

### CLI 選択
- 味方単体対象スキル選択時に味方一覧インデックスを表示
- 味方全体対象スキル選択時は対象選択をスキップ
- ターゲット入力失敗を個別ログで通知

### Skill Learning / Save 連携
- `data/master/skill_learns.sample.json` に支援系スキルを追加
- 従来の `unlocked_skill_ids` による使用可否を維持
- Save/Load の契約キーは変更なし（戦闘中ターゲット選択状態は保存対象外）

## 実行方法

- テスト実行:
  - `python -m unittest tests.test_battle_core tests.test_battle_target_selection tests.test_skill_learning_slice tests.test_playable_slice`
- 手動確認:
  - `python -m game.battle.cli.run_battle`
  - `python -m game.app.cli.run_game_slice`

## 今回のスコープ外
- 蘇生
- 継続回復（リジェネ）
- 戦闘中途中保存
- 高度な支援AI
- 装備連動の回復量補正

## 次の拡張ポイント
- `revive` 系 `effect_kind` 追加
- 全体バフ・継続回復の専用処理追加
- 支援優先のAIターゲットロジック追加
- 装備やステータス係数に応じた回復量計算式の高度化
