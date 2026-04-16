# Location Treasure Vertical Slice

## 今回の実装
- `data/master/location_rewards.sample.json` を追加し、ロケーション固定の探索報酬ノード（宝箱 / 固定発見物）を定義。
- `game/location` 配下に探索報酬モデル・サービス・マスターデータリポジトリを追加し、
  - 現在地にあるノード一覧表示
  - 開封可否判定（ロケーション一致、開封済み、必要フラグ、施設レベル）
  - 内容解決と inventory 反映の分離
  を実装。
- `PlayableSliceApplication` に探索報酬導線を統合し、`探索報酬を確認する` / `探索報酬を調べる` を追加。
- 開封済みノードIDを `meta.treasure_state.opened_reward_node_ids` として Save/Load で永続化。

## 対応した報酬種別
- 消耗品（例: `item.consumable.focus_drop`, `item.consumable.mini_potion`）
- 素材（例: `item.material.iron_fragment`）
- 装備（例: `equip.weapon.iron_blade`）
- レシピ書アイテム（例: `item.key.recipe_book.tidal_tonic_notes`）

## 既存導線との接続
- **Inventory / Equipment**: 探索報酬は inventory に加算され、装備アイテムは既存の装備変更導線でそのまま装着可能。
- **Recipe Discovery / Crafting**: レシピ書アイテム取得時に既存の `RecipeDiscoveryService` を再利用してレシピ解放ログを発火。
- **Location**: 現在地ごとに探索ノード一覧を返し、ロケーション不一致では開封失敗。
- **Quest / Flag**: `required_flags` でクエスト進行後に開封可能な発見物を表現。
- **Save**: 開封済みノードIDを保存し、Load後も再取得不可を維持。

## 実行方法
```bash
python -m game.app.cli.run_game_slice
```

- 拠点メニューの `探索報酬を確認する` でノード状態を確認。
- `探索報酬を調べる` で未開封ノードを開封。

## スコープ外
- 鍵アイテム消費
- 罠・ミミック
- ランダム配置
- 収集率UI

## 次の拡張候補
- `required_flags` の AND/OR 条件式化
- `required_facility_level` を使った施設成長連動宝箱の追加
- 会話イベントから探索ヒントを提示する演出ログの強化
