# PARTY_MENU_VERTICAL_SLICE

## 概要
本スライスでは Playable Vertical Slice の拠点メニューに、以下の最小ループを追加した。

- パーティ状態の確認（レベル / HP / SP / 基礎戦闘ステータス / EXP進行）
- 所持品確認
- 消耗品（HP回復 / SP回復）の使用
- 使用結果の在庫反映
- Save / Load 後の状態復元

## 実装範囲

### ステータス確認
`PlayableSliceApplication` の `status` アクションで以下を表示する。

- パーティ人数
- 最終イベントID
- ゴールド
- ワールドフラグ
- メンバー行（`member:{character_id}:lv=...:exp=...:hp=...:sp=...:atk=...:def=...:spd=...`）

### 所持品確認
`inventory` アクションで以下を表示する。

- ゴールド
- 所持アイテム一覧（`item:{item_id}:{name}:x{count}`）

### アイテム使用
`use_item` アクションで使用可能消耗品一覧を表示し、CLI から対象アイテムと対象メンバーを選択して `use_item(item_id, target_character_id)` を実行する。

- `ItemUseService` で使用可否判定を担当
  - 所持数
  - アイテム定義存在
  - 対象メンバー存在
  - target_scope / effect_type / effect_value の妥当性
  - 満タン時 no_effect
- 成功時
  - HP または SP を上限付きで回復
  - 在庫を 1 減算（0 以下で削除）

## マスターデータ
`data/master/items.sample.json` に消耗品の最小定義を追加。

- `item.consumable.mini_potion`（HP回復）
- `item.consumable.focus_drop`（SP回復）

各アイテムは以下を保持する。

- `item_id`
- `name`
- `item_type` / `category`
- `target_scope`
- `effect_type`
- `effect_value`
- `stackable`
- `description`

## Save / Load 接続
Save 契約の構造自体は変更していない。
`inventory_state` と `party_state.members[*].current_hp/current_sp` を既存仕様通り保存しているため、アイテム使用結果は Save / Load 後も保持される。

## 実行方法
```bash
python -m game.app.cli.run_game_slice --save-path tmp/playable_slice_slot_01.json
```

拠点メニューで以下を利用できる。

- ステータス確認
- 所持品確認
- アイテムを使う
- 受注中クエスト確認
- NPCと話す
- 討伐へ進む
- 報告する
- セーブする
- ロードする
- 終了する

## 今回のスコープ外
- 装備変更
- スキル習得UI
- 戦闘内アイテム使用
- 蘇生 / バフデバフの完成版
- 複数人パーティUI

## 次の拡張ポイント
- アイテム効果をデータ駆動で複合化（HP+SP、状態異常回復など）
- 複数対象（全体）や死亡対象など target_scope 拡張
- 戦闘内アイテム使用フローへの `ItemUseService` 再利用
- キャラクターマスタ連携による表示名 / クラス名の追加
