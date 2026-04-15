# RECIPE DISCOVERY VERTICAL SLICE

## 目的
- レシピ解放を「条件達成」だけでなく「発見イベント」として扱う最小導線を追加する。
- Quest / Dialogue / Loot Item からレシピ発見を発火し、工房NPCで状態を確認できるようにする。

## 今回の実装範囲
- `data/master/recipe_discoveries.sample.json` に発見定義を追加。
  - `unlock_source_type`: `quest_complete`, `dialogue_event`, `loot_item`
  - `source_id` と `recipe_ids` の静的対応を定義。
- `RecipeDiscoveryService` を追加。
  - 発見済みレシピとレシピ書の重複検知。
  - 不正 recipe_id の失敗検知。
- Playable Slice へ接続。
  - クエスト完了時に発見判定。
  - 会話イベント（工房NPC）選択時に発見判定。
  - アイテム獲得時（報酬/戦利品/採取）にレシピ書由来の発見判定。
  - `workshop_recipe:*` ログで工房NPCから発見状況を確認。
- Save連携。
  - `meta.crafting_state.discovered_recipe_ids`
  - `meta.crafting_state.discovered_recipe_book_ids`

## 責務分離
- master data: どの source でどの recipe が発見されるか。
- runtime state: 発見済み `recipe_id` / `recipe_book_id`。
- crafting unlock 条件評価（`RecipeUnlockService`）は維持し、発見イベントは `RecipeDiscoveryService` で扱う。

## 実行メモ
- `python -m unittest tests.test_crafting_slice tests.test_playable_slice`
- CLI: `python -m game.app.cli.run_game_slice`

## スコープ外
- 図鑑UI・カテゴリフィルタの完成版
- 工房ランク
- 工房施設拡張

## 次の拡張ポイント
- `recipe_unlock_event_id` ごとの演出ログテーブル追加
- `workshop_npcs.sample.json` に工房カテゴリ適性を追加
- レシピ書アイテム「使用」導線（現在は獲得時解放のみ）
