# STATUS EFFECT VERTICAL SLICE

## 概要
- 最小構成として **poison（毒）** と **defense_down（防御低下）** を実装。
- 毒は `per_turn`、防御低下は `while_active` の挙動で戦闘計算へ反映。
- 宿屋で `clear_on_rest=true` の効果を解除。
- 消耗品 `item.consumable.antidote_leaf` で `removable_by_item=true` の効果を解除。

## データ定義
- `data/master/status_effects.sample.json` に効果定義を追加。
- `skills.sample.json` の `effect_blocks` で `apply_effect` を参照。
- `items.sample.json` の `effect_type: cure_effect` と `remove_effect_ids` で解除対象を指定。

## スコープ内
- 1効果1インスタンスの最小管理（再付与時は残りターン上書き）。
- 戦闘内ターン経過で残りターン減少・期限切れ解除。
- Save/Load でパーティメンバーの `active_effects` を保持。

## スコープ外
- 命中率/耐性/属性耐性。
- 複数同種効果の重ねがけルール。
- 行動不能系状態異常、解除スキル、AI最適化。

## 拡張ポイント
- `StatusEffectDefinition` に resistance / dispel_category を追加。
- `application_rule` の種類を増やし、開始時/被弾時フックへ拡張。
- 効果優先度・スタック戦略を battle domain service に抽出。
