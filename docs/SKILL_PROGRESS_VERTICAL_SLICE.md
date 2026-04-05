# Skill Progress Vertical Slice（レベル到達によるスキル習得）

## 概要

Playable Slice に、**レベル到達でスキルを自動習得し、習得済みスキルのみ戦闘で利用する最小ループ**を追加した。

- マスターデータ: `skill_learns.sample.json` で「誰がいつ何を覚えるか」を定義
- ランタイム状態: `PartyMemberState.unlocked_skill_ids` で「現在習得済みのスキル」を保持
- 成長連携: レベルアップ時に `learned_skill:*` ログを出力
- 戦闘連携: 習得済みスキルのみを battle へバインド
- 永続化: Save / Load で習得済みスキルを保持

## 対応した習得条件

今回の最小実装では以下に対応:

- `character_id`
- `learnable_skills[]`
  - `skill_id`
  - `required_level`
  - `learn_type`（今回は `auto` のみ）
  - `description`（任意）

サンプルとして主人公 `char.main.rion` に以下を設定:

- Lv9: `skill.striker.venom_edge`（攻撃 + 毒付与）
- Lv10: `skill.striker.guard_break`（軽ダメージ + 防御低下、補助寄り）

## 接続方針

### Progression / Reward

- `ProgressionService` は既存どおりレベル計算のみを担当
- `SkillLearningService` を追加し、`RewardApplicationService` が「レベルアップ後の習得判定」を委譲
- `RewardApplicationService.apply()` は以下を順に処理
  1. EXP適用（レベルアップ判定）
  2. レベル上昇があれば習得判定
  3. 習得時に `learned_skill:{character_id}:{skill_id}:...` をログ出力

### Battle

- Quest/Battle 接続は既存方針を維持
- `PartyMemberState.unlocked_skill_ids` を battle 側の `bind_unit_skills()` に渡し、利用可能スキルを制限
- 未習得スキルはバインドされないため、コマンド候補に出ず利用不可

### Save

- 既存 `unlocked_skill_ids` フィールドをそのまま利用
- 契約バージョンは `v1` を維持（破壊的変更なし）

### Playable Slice

- New Game 時の初期スキルは `characters.sample.json` 由来
- `status` 表示の `member:*` 行に `skills=[...]` を追加
- レベルアップ後は `learned_skill:*` ログで確認可能

## 実行方法

```bash
python -m unittest tests.test_skill_learning_slice tests.test_playable_slice tests.test_progression_rewards
python -m unittest
python -m game.app.cli.run_game_slice
```

## 今回のスコープ外

- スキルツリーUI
- 分岐習得 / 選択式習得
- ジョブ / クラス
- パッシブスキル
- スキル装備枠
- スキル強化

## 次に自然につながる拡張ポイント

- `learn_type` に `quest_unlock` / `item_unlock` / `job_unlock` を追加
- 複数パーティメンバー対応の学習テーブル拡張
- バトルコマンドUIで習得済みスキル一覧を対話選択化
- 装備依存スキルや派生習得（前提スキル）判定の追加
