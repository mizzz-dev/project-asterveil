# HUB FACILITY PROGRESSION VERTICAL SLICE

## 目的
- 依頼達成によって拠点施設が成長し、工房レシピとショップ在庫が段階的に解放される最小ループを提供する。
- master data（施設定義）と runtime state（現在レベル・解放状態）を分離する。

## 今回の実装範囲
- `data/master/hub_facilities.sample.json` に施設定義を追加。
  - `facility.hub.workshop`（工房）
  - `facility.hub.general_store`（ショップ）
- 施設レベルは `level 1 -> 2` のみを実装。
- 条件は以下を採用。
  - 完了クエストID
  - 納品完了回数（`required_turn_in_count`）
- 解放は以下を採用。
  - レシピID
  - ショップ在庫ID
  - 会話フラグ

## 接続方針

### Quest / Turn-in
- `PlayableSliceApplication._complete_quest` で、`turn_in_items` objective を含むクエスト完了時に納品完了回数を加算。
- クエスト完了時、および納品処理時に `FacilityProgressService` を評価する。
- repeatable quest は施設成長の主条件に使わず、一回限りの進行クエストを優先した（重複成長を避けるため）。

### Crafting
- 既存の「レシピを知っている/解放済み」判定は `RecipeUnlockService` を継続利用。
- 追加で「施設側で許可されたレシピか」を判定し、両方を満たした時だけ作成可能とする。
- 施設条件を満たさない場合は `craft_failed:required_workshop_rank` を返す。
- 工房会話・クラフト一覧に `workshop_rank` を表示。

### Shop
- 既存 `ShopService` は変更せず、Playable層で施設解放済み在庫のみ表示/購入可能に制御。
- 非解放在庫は一覧から隠し、購入時は `purchase_failed:shop_stock_locked` を返す。

### Dialogue
- 工房NPCにランク1/ランク2会話を追加。
- ランク2到達時に新設計図会話（`dialogue.workshop.rank2_blueprint`）を通じて新レシピ発見を案内。

### Save / Load
- `meta.facility_state` を追加。
  - `facility_levels`
  - `unlocked_recipe_ids`
  - `unlocked_shop_stock_ids`
  - `turn_in_completion_count`
- Load時に復元後、初期レベル解放と再評価を行う。

## 実行方法
- 全体テスト:
  - `python -m unittest`
- 施設進行の主確認:
  - `python -m unittest tests.test_facility_progression_slice`
- 手動確認:
  - `python -m game.app.cli.run_game_slice`

## 今回のスコープ外
- 宿屋ランク
- 複数施設同時改築演出
- 街全体復興メーター
- 分岐型施設成長

## 次の拡張ポイント
- 施設ごとの経験値/ポイント蓄積
- 施設成長トリガーの重み付け（納品品質・カテゴリ別）
- 施設UIの詳細化（改築履歴・次条件）
