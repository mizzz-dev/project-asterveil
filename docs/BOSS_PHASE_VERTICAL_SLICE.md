# BOSS PHASE VERTICAL SLICE

## 目的

本スライスは、**ボス戦フェーズ遷移 / 条件分岐行動 / 戦闘中イベント**を、既存 Battle / Enemy AI / Quest / Playable Slice に接続する最小実装です。

## 今回の対応範囲

- `data/master/boss_encounters.sample.json` を追加し、ボス encounter と phase 定義をデータ駆動化。
- `encounter.ch01.tide_serpent_boss` を追加し、2フェーズのボス戦を実装。
  - Phase1: 毒付与寄り（`enemy_ai.tide_serpent.phase1`）
  - Phase2: HP 50% 以下で遷移し、全体攻撃寄り（`enemy_ai.tide_serpent.phase2`）
- フェーズ遷移時に戦闘ログへ台詞を出力し、自己強化（`effect.buff.attack_up`）を適用。
- 既存 Quest / Location へ接続し、ボス討伐クエスト `quest.ch01.tide_serpent_subjugation` を追加。
- Save 方針は既存を維持（戦闘中 phase 状態は保存対象外）。

## データ定義

- ボス定義: `data/master/boss_encounters.sample.json`
  - `encounter_id`
  - `boss_enemy_id`
  - `phases[]`
    - `phase_id`
    - `enter_condition`（最小対応: `hp_ratio_below`）
    - `ai_profile_id`
    - `on_enter_events`（`show_message`, `apply_effect_to_self`, `set_flag`）

## 実装の責務分離

- `game/battle/infrastructure/master_data_repository.py`
  - ボス定義の読み込み・検証。
- `game/battle/application/boss_phase.py`
  - フェーズ状態（runtime）
  - 条件判定
  - 一度きり遷移制御
  - on-enter イベント実行
- `game/battle/application/session.py`
  - 敵AI実行前にフェーズ解決を呼び、適用すべき `ai_profile_id` を切替。
  - 通常敵には影響なし（boss定義がある encounter のボスのみ適用）。

## Quest / Location / Playable Slice 接続

- `quest.ch01.tide_serpent_subjugation` を追加。
- `location.dungeon.tidegate_ruins` を追加し、`flag.ch01.harbor_secured` で開放。
- `PlayableSliceApplication._run_hunt` は、アクティブクエストの `encounter_id` を優先利用。
  - クエストの encounter が現在地に含まれない場合は失敗ログを返す。

## Save / Load 方針

- 戦闘中の `BossPhaseState` は保存しない。
- 既存どおり、戦闘後の quest progress / world_flags / party state / inventory は保存。
- ボス撃破は quest 完了フラグ（`flag.ch01.tide_serpent_subjugated`）で永続化。

## 実行方法

- 全体テスト
  - `python -m unittest`
- ボスフェーズ関連テストのみ
  - `python -m unittest tests.test_boss_phase_slice -v`

## 今回のスコープ外

- 3フェーズ以上
- 召喚雑魚
- 戦闘中会話分岐
- 専用カットイン/UI
- 戦闘中途中保存

## 次の拡張ポイント

- `enter_condition` の追加（ターン数、取り巻き生存数、状態異常有無）
- `on_enter_events` の拡張（専用演出ID発火、BGM切替イベント橋渡し）
- ボス専用の複合AI条件（phase + 状況判定）
