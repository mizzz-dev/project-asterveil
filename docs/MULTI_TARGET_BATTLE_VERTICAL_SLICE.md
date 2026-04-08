# MULTI TARGET BATTLE VERTICAL SLICE

## 概要

本スライスでは、既存の 1vs1 戦闘を壊さずに、以下の最小要件を追加した。

- encounter マスターデータから複数敵編成を読み込む
- 単体対象 (`single_enemy`) と全体対象 (`all_enemies`) を行動側で使い分ける
- 撃破済み対象を選択できないようにする
- 全敵撃破で勝利判定になる既存ルールを複数敵で成立させる
- Quest / Playable Slice / Save 既存導線と整合する

## 実装範囲

### encounter 定義

- `data/master/encounters.sample.json` を追加
  - 単体編成: `encounter.ch01.port_wraith_single`
  - 同種複数編成: `encounter.ch01.port_wraith`
  - 異種混成編成: `encounter.ch01.harbor_miasma_patrol`

### battle ドメイン

- `target_scope` ベースで対象解決を分離
  - `single_enemy` は `target_id` 必須
  - `all_enemies` は生存中の敵全体へ適用
- スキル効果・ダメージを対象ごとに適用できるように最小拡張

### skill 定義

- `skills.sample.json` に `target_scope` を追加
- 全体攻撃スキル `skill.striker.arc_wave` を追加
- 単体デバフ/状態異常系は既存 `flare_slash` / `venom_edge` を継続利用

### Quest / Playable Slice / Save 接続

- Battle 実行は encounter 定義を参照して敵パーティを構築
- 戦闘中のターゲット選択入力状態は保存対象外
- 戦闘結果（HP/SP/生存/状態異常）や quest progress は既存 save フローを継続利用

## 実行方法

- バトル CLI 実行:
  - `python -m game.battle.cli.run_battle`
- テスト実行:
  - `python -m unittest tests.test_battle_core tests.test_skill_learning_slice`
  - `python -m unittest`

## 今回のスコープ外

- 味方対象スキル
- 列対象 / ランダム多段対象
- 途中セーブ（戦闘中スナップショット）
- 高度なターゲットUI

## 次の拡張ポイント

- `target_scope` に `ally_single` / `ally_all` / `row_enemy` を追加
- `target_count` を使ったランダム n 体対象
- 行動選択とターゲット選択の UI レイヤを battle ドメインから分離したまま強化
