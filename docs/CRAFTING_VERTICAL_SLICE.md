# CRAFTING_VERTICAL_SLICE

## 目的

戦利品・購入品として得た素材を `inventory_state` から消費し、消耗品/装備を生成する最小クラフトループを提供する。

## 今回の対応範囲

- マスターデータ `data/master/crafting_recipes.sample.json` でレシピを定義
- `CraftingMasterDataRepository` でレシピ読み込みと最小バリデーション
- `CraftingService` で以下を実装
  - 素材所持チェック
  - クラフト可否判定
  - 素材消費
  - 生成物付与
  - 同一出力IDの集約
- Playable Slice の拠点メニューからクラフト導線を追加

## レシピ定義

- `recipe.craft.memory_tonic` (消耗品)
  - 素材: `item.material.memory_shard`, `item.consumable.antidote_leaf`
  - 生成: `item.consumable.memory_tonic`
- `recipe.craft.memory_edge` (装備)
  - 素材: `item.material.memory_shard`, `item.material.iron_fragment`
  - 生成: `equip.weapon.memory_edge`

## 既存導線との接続

- Loot: `item.material.memory_shard` を戦闘報酬として入手し、そのままクラフト素材に利用
- Shop: `item.material.iron_fragment` を購入し、そのままクラフト素材に利用
- Inventory: 素材判定/消費/生成はすべて `inventory_state["items"]` を利用
- Item Use: クラフト生成した `item.consumable.memory_tonic` を既存 `ItemUseService` で使用可能
- Equipment: クラフト生成した `equip.weapon.memory_edge` を既存 `EquipmentService` で装備可能
- Save/Load: クラフト結果は inventory/equipped に反映された状態で既存セーブ契約に保存される

## 実行方法

- 全体テスト: `python -m unittest`
- クラフト関連テスト: `python -m unittest tests.test_crafting_slice`
- 手動確認: `python -m game.app.cli.run_game_slice`

## スコープ外

- 成功率付きクラフト
- レシピ解放イベント
- クラフトレベル
- 派生合成ツリー
- 大量一括クラフト
- 強化/分解システム

## 次の拡張ポイント

- `unlock_flags` を world_flags と接続してレシピ解放を実装
- クラフト施設/場所依存条件の追加
- `count > 1` を UI フローへ開放
- レシピ入手（クエスト報酬・ドロップ）を追加
