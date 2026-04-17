# ADVANCED WORKSHOP CRAFTING VERTICAL SLICE

## 目的

- フィールドミニボス素材と探索希少素材の使い道を、工房高ランク限定クラフトへ接続する。
- 既存の Crafting / Recipe Discovery / Workshop Rank / Equipment Passive / Save を流用し、最小差分で上位クラフト体験を追加する。

## 今回の実装範囲

- `data/master/crafting_recipes.sample.json` に上位レシピ `recipe.craft.tidebreaker_harness` を追加。
  - `recipe_tier: advanced`
  - `required_workshop_level: 3`
  - `required_recipe_discovery: recipe_book.astel.tidebreaker_notes`
  - 素材に `item.material.miniboss.guardian_core`（ミニボス）と `item.material.relic.deepsea_thread`（探索報酬）を要求。
- ミニボス報酬に `guardian_core`、探索報酬に `deepsea_thread` を追加。
- 上位生成物として `equip.armor.tidebreaker_harness` を追加。
  - 既存 `battle_start_effect` passive（防御上昇付与）を利用。
- Playable Slice のクラフト表示・実行判定に以下を追加。
  - レシピごとの `required_workshop_level` 判定
  - `required_recipe_discovery` 判定
  - 状態タグ表示 `[未発見] [工房ランク不足] [素材不足] [作成可能]`
  - 補助ログ `advanced_recipe_unlocked:*`, `advanced_crafting_success:*`, `requires_miniboss_material:*`
- 工房NPC会話にランク不足/ランク到達時の上位レシピ案内差分を追加。

## 既存導線との接続

- **Field Miniboss**: `miniboss.ch01.tidal_flats.shrine_guardian` 初回報酬で `guardian_core` を獲得。
- **Location Treasure**: `reward.discovery.tidal_flats_hidden_cache` から `deepsea_thread` を獲得。
- **Workshop Rank**: `workshop_orders.sample.json` の rank 3（progress 120）で上位レシピを解放対象に追加。
- **Recipe Discovery**: 工房NPC会話 `dialogue.workshop.rank3_blueprint` でレシピ書IDを発見し、上位レシピ利用条件を満たす。
- **Equipment Passive**: 生成した `equip.armor.tidebreaker_harness` を既存装備導線で装備可能。
- **Save/Load**: 既存 `inventory_state` / `meta.crafting_state` / `meta.workshop_state` 保存により状態保持（契約キー追加なし）。

## 実行方法

- 全体テスト: `python -m unittest`
- クラフト関連: `python -m unittest tests.test_crafting_slice`
- 手動確認: `python -m game.app.cli.run_game_slice`

## 今回のスコープ外

- 装備品質ランク・ランダムオプション
- 大成功/失敗クラフト
- 専用演出や鍛冶ミニゲーム
- エンドゲーム向けの多段強化システム

## 次の拡張ポイント

- レシピ書アイテムを「使用」して学習する導線の追加
- 上位クラフト専用の repeatable 工房依頼追加
- 工房ランク4以降と複数上位レシピカテゴリへの展開
