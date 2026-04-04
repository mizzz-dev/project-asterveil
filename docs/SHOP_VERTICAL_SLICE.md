# Shop Vertical Slice

## 概要

Playable Slice の拠点メニューから利用できる、最小のショップ/購入フローを追加した。

- 拠点メニューから `ショップに行く` を選択可能
- ショップの販売アイテム一覧と価格を確認可能
- gold を消費して消耗品を購入可能
- 購入結果は既存 inventory に反映
- Save / Load 後も gold と inventory が保持される

## 実行方法

```bash
python -m game.app.cli.run_game_slice
```

1. `New Game` を選択
2. 拠点メニューで `ショップに行く` を選択
3. 一覧から購入アイテムを選択
4. `所持品確認` / `アイテムを使う` で反映を確認
5. `セーブする` → `終了する` → `Continue / Load` で状態復元を確認

## 設計方針（最小構成）

- **マスターデータ**: `data/master/shops.sample.json` に「何をいくらで売るか」を定義
- **ランタイム状態**: `inventory_state.gold` と `inventory_state.items` に所持金/所持数を保持
- **購入基盤**:
  - `ShopMasterDataRepository`: ショップ定義読込
  - `ShopService`: 購入可否判定と反映

今回の在庫は `stock_type: "unlimited"` のみ運用。`stock_limit` フィールドを定義可能にし、将来の固定在庫に拡張しやすい構造にしている。

## 対応している失敗ケース

- 不正 `shop_id`
- 不正 `item_id`（その店で販売されていない）
- 不足 gold
- 不正 quantity
- アイテム定義不備（items マスター未定義）

## Save/Load 接続

既存 Save 契約の `inventory_state` を再利用し、追加の save schema 変更は行っていない。

- 保存対象: `inventory_state.gold`, `inventory_state.items`
- ロード時: 既存復元処理で購入後状態をそのまま復元

## 今回のスコープ外

- 売却
- 装備品販売
- 複数店舗運用
- 在庫制限の完成版
- 価格変動 / 割引
- まとめ買い UI

## 次の拡張ポイント

- quantity 入力 UI とまとめ買い
- 店舗ごとの在庫管理（固定在庫/日次補充）
- 売却フロー（買値/売値）
- 店舗解放条件（クエスト進行連動）
