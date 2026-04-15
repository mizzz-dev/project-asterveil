# RECIPE_UNLOCK_VERTICAL_SLICE

## 目的

クエスト進行やフラグ成立に応じてレシピを解放し、**解放済みレシピのみクラフト可能**にする最小進行ループを追加する。

## 今回の対応範囲

- `data/master/crafting_recipes.sample.json` に以下を追加
  - `unlock_conditions`
    - `required_flags`
    - `required_completed_quest_ids`
    - `required_location_ids`
  - `visible_before_unlock`
  - `unlock_message`
- `RecipeUnlockService` を追加し、解放条件評価を `CraftingService` から分離
- Playable Slice で、クエスト報告・会話フラグ成立時にレシピ解放評価を実施
- クラフト一覧で `解放済み/未解放` と `素材充足/素材不足` を表示
- セーブの `meta.crafting_state.unlocked_recipe_ids` に解放済みレシピIDを保存

## レシピ解放例（サンプルデータ）

- `recipe.craft.memory_tonic`
  - 初期解放（条件なし）
- `recipe.craft.memory_edge`
  - `quest.ch01.missing_port_record` 完了で解放
- `recipe.craft.herbal_focus_drop`
  - `flag.helped_npc` 成立で解放

## 既存導線との接続

- Quest: `report_ready_quest()` 後に解放判定を実行
- Dialogue Event: `set_flag` / `set_flags` の適用後に解放判定を実行
- Crafting: 未解放時は `craft_failed:recipe_locked:*` を返す
- Save/Load: `meta.crafting_state.unlocked_recipe_ids` を保存・復元
- Playable Slice: クラフト一覧で状態確認、解放時に `recipe_unlocked:*` ログ表示

## 実行方法

- 全体テスト: `python -m unittest`
- クラフト関連テスト: `python -m unittest tests.test_crafting_slice`
- プレイアブル導線テスト: `python -m unittest tests.test_playable_slice`

## スコープ外

- レシピ書アイテム実装
- 工房レベルやカテゴリ段階解放
- 複雑な派生ツリー
- 解放演出UI

## 次の拡張ポイント

- `required_location_ids` を利用した施設/エリア依存解放
- レシピ書・NPC師匠・施設レベルを `unlock_conditions` に段階追加
- レシピヒント表示（未達成条件の人間可読メッセージ）
