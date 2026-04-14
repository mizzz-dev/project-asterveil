# CONTENT SCHEMA (MVP / Vertical Slice)

## 1. 目的

本書は Vertical Slice〜MVP で扱うコンテンツデータの**最小契約**を定義する。対象はマスターデータとセーブデータ双方。

---

## 2. ID命名ルール

- 形式: `<category>.<group>.<name>`
- 文字種: `a-z`, `0-9`, `_`, `.` のみ
- 例:
  - `char.main.rion`
  - `skill.striker.flare_slash`
  - `quest.ch01.missing_port_record`
  - `event.ch01.boss_intro`

### ルール
- IDは永続キーとして扱い、**リネーム禁止**（廃止時はdeprecated化）。
- 表示名や文言はIDではなくローカライズテーブルで管理する。

---

## 3. マスターデータ定義

## 3.1 キャラクター定義 (CharacterDefinition)

**必須**
- `id`
- `role` (`vanguard|striker|tactician|healer|disruptor`)
- `base_stats` (`hp`,`atk`,`def`,`spd`)
- `growth_curve_id`
- `initial_skill_ids[]`

**任意**
- `resistance_profile_id`
- `lore_tags[]`
- `ai_profile_id` (NPC利用時)

## 3.2 スキル定義 (SkillDefinition)

**必須**
- `id`
- `target_type`（実装最小値: `single|all`）
- `target_scope`（実装最小値: `single_enemy|all_enemies`）
- `cost` (`sp`,`cooldown`)
- `effect_blocks[]`（ダメージ/回復/付与）
- `weight`

**任意**
- `target_count`（`all_enemies` の先頭N体対象などの拡張用）
- `break_power`
- `combo_tag`
- `precast_warning`

## 3.3 装備定義 (EquipmentDefinition)

**必須**
- `id`（実データでは `equipment_id` も許容）
- `slot` (`weapon|armor|accessory`)（実データでは `slot_type` も許容）
- `stat_modifiers`

**任意**
- `rarity`
- `passive_effects[]`
  - `passive_id`
  - `passive_type`（最小: `status_resistance|heal_bonus|battle_start_effect|sp_cost_modifier|stat_bonus`）
  - `target`（最小: `self`）
  - `parameters`（型ごとの追加パラメータ）
  - `description`
- `set_id`

## 3.4 敵定義 (EnemyDefinition)

**必須**
- `id`
- `level`
- `stats`
- `weakness`（属性/武器）
- `skill_rotation_id`
- `drop_table_id`

**任意**
- `phase_transitions[]`
- `enrage_rule`

## 3.5 クエスト定義 (QuestDefinition)

**必須**
- `id`
- `quest_type` (`main|sub|character|exploration|bounty`)
- `chapter`
- `prerequisites[]`
- `objectives[]`
- `rewards`

**任意**
- `fail_conditions[]`
- `world_state_changes[]`

## 3.6 会話/イベント定義 (Conversation/Event Definition)

**必須**
- `id`
- `scene_id`
- `lines[]`（speaker, text_key, emotion）
- `triggers[]`
- `next_event_ids[]`

**任意**
- `choice_branches[]`
- `camera_cues[]`

## 3.7 エンカウント定義 (EncounterDefinition)

**必須**
- `encounter_id`（後方互換として `id` も許容）
- `enemies[]`
  - `enemy_id`
  - `count`（省略時は `1`）

**任意**
- `description`
- `enemies[].slot`（将来の列/位置拡張用メタ情報）

**後方互換メモ**
- 旧形式 `enemy_id` 単独指定も最小実装では読み込み許容とする。

## 3.8 敵AI定義 (EnemyAiProfile)

**必須**
- `ai_profile_id`
- `action_rules[]`
  - `rule_id`
  - `priority`
  - `action_type`（`normal_attack|skill`）
  - `target_rule`（最小実装: `lowest_hp_enemy|random_enemy|self|lowest_hp_ally`）

**任意**
- `skill_id`（`action_type=skill` 時）
- `conditions[]`
  - 例: `self_hp_below_ratio`, `enemy_has_no_effect`, `ally_needs_heal`, `ally_count_alive_at_least`

---

## 4. セーブ対象データ (SaveData v1)

**必須**
- `save_version`
- `player_profile`（難易度、プレイ時間、最終保存時刻）
- `party_state`（所持キャラ、レベル、装備、スキル解放）
- `quest_state`（受注状態、進行カウンタ）
- `world_flags`（章進行、イベント完了）
- `inventory_state`

**任意**
- `telemetry_opt_in`
- `tutorial_seen_flags`
- `last_checkpoint`

**保存しないもの（再計算対象）**
- 一時UI状態
- マスター原本
- キャッシュ生成物

---

## 5. 将来エンドコンテンツ拡張を想定した拡張項目

- `challenge_tier`（高難度層）
- `season_id`（季節イベント）
- `affix_pool_id`（ランダム特性）
- `raid_rule_set_id`（協力ルール）

MVPでは未使用でも、予約フィールドとして schema 上に optional で許容する。

---

## 6. バリデーション観点

- 参照整合: すべての参照IDが存在する
- 重複禁止: 同一IDの重複定義なし
- 列挙妥当性: role/slot/type が許可値内
- 範囲妥当性: 数値（weight, cost, stat）が許可範囲内
- 進行妥当性: quest prerequisites が循環しない
- ローカライズ整合: text_key 未定義がない

---

## 7. データ更新時の互換性注意点

1. 既存IDの意味変更を避ける（互換性破壊）。
2. フィールド削除よりも `deprecated` マークを優先。
3. SaveData は `save_version` でマイグレーション関数を必須化。
4. クエスト objective の順序変更は既存進行へ影響するため、差分移行手順を用意する。

---

## 8. サンプル配置

- `data/master/*.sample.json` に最小サンプルを配置
- `data/save_contract/save_data_v1.sample.json` にセーブ契約サンプルを配置
