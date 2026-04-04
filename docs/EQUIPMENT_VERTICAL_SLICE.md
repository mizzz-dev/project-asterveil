# Equipment Vertical Slice（最小装備ループ）

## 今回実装した内容

- `weapon` / `armor` の2スロットを持つ最小装備システムを追加。
- 装備マスター（`data/master/equipment.sample.json`）から装備定義を読み込み。
- ショップ購入 → 所持品反映 → 装備変更 → ステータス反映までを接続。
- Save / Load で `party_state.members[].equipped` をそのまま永続化・復元。
- Playable Slice の拠点メニューに `装備変更` 導線を追加。

## 装備スロットとデータ境界

- **マスター定義**: 装備ID、名前、スロット、能力補正、説明、価格。
- **ランタイム状態**: 誰が何を装備しているか（`PartyMemberState.equipped`）。
- **インベントリ**: 所持個数（`inventory_state.items`）。

装備変更時は「所持個数 - パーティ全体で装着中個数」を利用して在庫整合を判定し、重複装着による消失/複製を防ぐ最小方式にしています。

## ステータス反映

- `EquipmentService.resolve_final_stats` で以下を合成:
  - ベース値（成長済みの `PartyMemberState`）
  - 装備補正（`stat_modifiers`）
- 反映対象:
  - `hp / sp / atk / defense / spd`
  - `status` 表示 / パーティ表示
  - 討伐時のバトル入力ステータス

## Shop / Save / Battle 連携

- **Shop**: 装備品を `shops.sample.json` に追加し、既存購入処理を再利用。
- **Save**: 既存 `equipped` フィールドを活用し、追加破壊的変更なし。
- **Battle**: 討伐実行直前に最終ステータスを組み立て、battle executor へ渡す。

## 実行方法

```bash
python -m game.app.cli.run_game_slice
python -m unittest -q
```

## 今回のスコープ外

- アクセサリ等の追加スロット
- 売却、装備比較UI、装備条件
- 特殊パッシブ、割合補正
- 装備強化、ランダムオプション

## 次の拡張ポイント

- スロット追加（accessory など）と装備条件
- `inventory_state` を装備専用コンテナへ分離
- バトル中の特殊効果フック（状態異常耐性など）
- 売却と装備比較表示
