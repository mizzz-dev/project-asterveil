# EQUIPMENT SALVAGE VERTICAL SLICE

## 概要
- 工房導線に「装備分解（リサイクル）」を追加し、不要装備を素材へ還元する最小ループを実装した。
- 分解定義は `data/master/equipment_salvage.sample.json` に分離し、master data と runtime state の責務を分離した。
- 既存のクラフト・装備強化・工房ランク・Save/Load と接続し、素材循環を成立させた。

## 今回の対応範囲
- マスターデータ
  - `equipment_id` ごとに `salvage_enabled` / `required_workshop_level` / `base_returns` / `upgrade_bonus_returns` / `salvage_tags` / `description` を定義。
  - 通常装備（`equip.weapon.bronze_blade`）と上位装備（`equip.armor.tidebreaker_harness`）の分解例を追加。
- アプリケーション
  - `EquipmentSalvageService` で分解可否判定・還元解決・在庫反映を実装。
  - 装備中のみ所持している場合は分解不可（`equipment_salvage_failed:equipped:*`）。
  - 工房ランク不足時は分解不可（`equipment_salvage_failed:insufficient_workshop_level`）。
  - 分解成功時は装備を1つ消費し、素材還元ログ（`equipment_salvage_return:*`）を返す。
- 強化済み装備方針
  - 強化済み装備も分解可能。
  - `upgrade_bonus_returns` を「強化段階 × 数量」で加算して還元。
  - 分解後に対象装備が在庫0になった場合、`equipment_upgrade_levels` をクリーンアップする。
- Playable Slice 統合
  - 拠点メニューに `salvage_equipment`（装備分解）を追加。
  - 工房NPC会話時に分解ガイダンスと分解可能状態を表示。
  - CLI から分解対象を選択可能。
- Save/Load
  - 追加保存項目は不要。
  - 既存 `inventory_state` と `meta.equipment_state.upgrade_levels` の更新結果をそのまま保存・復元する。

## 導線
1. 工房メニュー `装備分解` を選択。
2. 分解対象を選び、可否タグ（`[分解可能] [装備中] [工房ランク不足]`）を確認。
3. 分解成功で `equipment_salvage_success:*` と `equipment_salvage_return:*` が出力される。
4. 還元素材を既存 `クラフト` / `装備強化` に再利用できる。

## 実行方法
- CLI: `python -m game.app.cli.run_game_slice --save-path tmp/playable_slice_slot_01.json`
- テスト:
  - `python -m unittest tests.test_equipment_salvage_slice`
  - `python -m unittest tests.test_playable_slice tests.test_equipment_upgrade_slice`

## 今回のスコープ外
- 分解成功率
- 一括分解
- ランダム還元
- 品質継承
- 専用演出

## 次の拡張ポイント
- 分解対象の個体ID管理（同一 equipment_id の個別強化段階を将来区別）
- 分解専用クエスト/会話分岐（初回解禁チュートリアル）
- salvage_tags を使った施設効果（例: `miniboss` タグ分解ボーナス）
