# FIELD_MINIBOSS_VERTICAL_SLICE

## 概要
- フィールド分岐イベントの危険な選択肢から、任意遭遇のミニボス戦へ遷移する最小導線を追加。
- ミニボス定義を `data/master/miniboss_encounters.sample.json` でデータ駆動化。
- 初回撃破報酬と通常戦利品を分離し、初回報酬の二重受取を防止。
- 撃破状態と初回報酬受取状態を `meta.miniboss_state` に保存し、Save/Load 復元に対応。

## 追加したデータ
- `data/master/miniboss_encounters.sample.json`
  - `miniboss_id`
  - `encounter_id`
  - `location_id`
  - `trigger_event_id`
  - `display_name`
  - `first_clear_rewards`
  - `repeat_rewards`
  - `defeat_flag`
  - `repeatable`
  - `description`
- `data/master/location_events_branching.sample.json`
  - `event.field.tidal_flats.sunken_shrine_switch` を追加。
  - `choice.pull_lever` で `start_miniboss_battle` を実行。
- `data/master/dialogues.sample.json`
  - ミニボス撃破前ヒント会話 / 撃破後会話差分を追加。

## 実装ポイント
- `game/location/domain/miniboss_entities.py`
  - `MinibossDefinition`, `MinibossStartResult`, `MinibossRewardResolution` を定義。
- `game/location/infrastructure/miniboss_repository.py`
  - マスターデータ読み込みと最低限の整合性検証を実装。
- `game/location/domain/miniboss_service.py`
  - 実行可否判定（ID不正 / trigger不一致 / location不一致 / 再戦不可）
  - 初回報酬・再戦報酬の解決
  - フィールドイベント一覧向けの状態ラベル生成
- `game/app/application/playable_slice.py`
  - `start_miniboss_battle` outcome 対応
  - ミニボス戦開始ログ・撃破ログ・初回報酬ログを追加
  - `meta.miniboss_state` の save/load 対応

## 責務境界
- Field Event:
  - どの選択でミニボスを起動するかのみ定義。
- Battle:
  - 既存 `_run_event_battle` を流用（戦闘本体の重複実装なし）。
- Miniboss:
  - 実行可否 / 初回判定 / 特別報酬解決を専用サービスで管理。
- Recipe Discovery:
  - 初回報酬で得たレシピ書アイテムを既存 `discover_from_items` 導線に接続。
- Save:
  - `meta.miniboss_state` に runtime state のみ保存。

## 現在の方針
- `repeatable=false` のみを実運用対象とし、初回撃破後は再戦不可。
- `repeat_rewards` は将来の `repeatable=true` 拡張用に定義可能だが、今回サンプルでは再戦不可のため利用しない。

## 実行例
- `python -m unittest tests.test_field_miniboss_slice -v`
- `python -m unittest tests.test_field_branch_event_slice -v`
- `python -m unittest tests.test_playable_slice -v`

## スコープ外
- ミニボス専用複数フェーズ
- ミニボス再戦周回報酬設計
- ミニボス専用演出・カットシーン
- ランダム出現ミニボス

## 次の拡張ポイント
- `repeatable=true` 向け再戦報酬テーブルとクールダウン制御
- ミニボス撃破による施設成長トリガー追加
- ロケーション探索報酬（treasure node）との連動拡張
