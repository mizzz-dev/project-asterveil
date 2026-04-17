# EQUIPMENT UPGRADE VERTICAL SLICE

## 概要
- 工房でクラフトした上位装備を、素材消費と工房ランク条件で段階強化できる最小導線を追加した。
- 対象は `equip.armor.tidebreaker_harness` のみで、2段階の強化を定義した。
- 強化段階はランタイム状態（`equipment_upgrade_levels`）として保持し、Save/Load 後も復元される。

## 今回の対応範囲
- マスターデータ
  - `data/master/equipment_upgrades.sample.json` を追加。
  - 強化段階ごとに `required_workshop_level` / `required_items` / `stat_bonus` / `description` を定義。
- アプリケーション
  - `EquipmentUpgradeService` で強化可否判定、素材消費、段階更新を実装。
  - `PlayableSliceApplication` に工房メニュー導線（`upgrade_equipment`）を追加。
  - 工房NPC会話時に強化状況と必要素材・必要ランクを表示。
- 装備性能反映
  - `EquipmentService` に強化ボーナス解決処理を追加。
  - 強化段階に応じて最終 `hp` / `defense` が上昇し、戦闘前の最終ステータス計算へ反映。
- Save/Load
  - `meta.equipment_state.upgrade_levels` を保存・復元。

## 導線
1. 工房ランク3到達後、`recipe.craft.tidebreaker_harness` をクラフト。
2. 工房メニュー `装備強化` または工房NPC会話で必要素材/ランクを確認。
3. 条件を満たすと `equipment_upgrade_success:*` が出力され、素材を消費して段階が進む。
4. `status` / `equipment` / `hunt` 時のステータスで強化結果を確認可能。

## 実行方法
- CLI: `python -m game.app.cli.run_game_slice --save-path tmp/playable_slice_slot_01.json`
- テスト: `python -m unittest tests.test_equipment_upgrade_slice tests.test_playable_slice tests.test_crafting_slice`

## 今回のスコープ外
- ランダムオプション付与
- 強化失敗
- 継承/分岐進化
- GUI専用演出

## 次の拡張ポイント
- 強化段階に応じた passive_modifiers の動的適用
- 複数装備カテゴリへの強化定義展開
- 強化専用クエスト/会話差分の拡張
