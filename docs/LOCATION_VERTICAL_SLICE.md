# Location Vertical Slice

## 今回の実装
- `data/master/locations.sample.json` に、拠点 (`location.town.astel`) と討伐先ロケーションを追加。
- `game/location` モジュールを新設し、ロケーション定義読み込み (`LocationMasterDataRepository`) と移動処理 (`TravelService`) を分離。
- `PlayableSliceApplication` に現在地・解放済みロケーション状態を追加し、移動と討伐導線を接続。

## 接続ポイント
- **クエスト接続**: `quests.sample.json` に `target_location_id` を持たせ、討伐対象クエストの推奨ロケーションを紐づけ。
- **戦闘接続**: 現在地ロケーションの `default_encounter_id` から戦闘開始。勝敗は既存 battle / reward / quest progress 更新を再利用。
- **帰還仕様（最小）**: 戦闘後は `can_return_to_hub=true` のロケーションから自動で拠点へ帰還。
- **Save 接続**: `meta.location_state` に `current_location_id` と `unlocked_location_ids` を保存・復元。

## 実行方法
- CLI ランナー: `python -m game.app.cli.run_game_slice`
- 拠点メニューから `移動する` で討伐先へ移動し、`討伐へ進む` を実行。

## スコープ外
- フリーマップ探索、座標移動、ランダムエンカウント
- ダンジョン階層、採取ポイント、地形ギミック
- 複雑な通行制限やファストトラベル完成版

## 次の拡張候補
- ロケーションごとの複数 encounter 選択 UI
- unlock_condition の条件式化（フラグ AND/OR、クエスト状態参照）
- 複数拠点 + 拠点間ルート
- ロケーション内イベントや採取ポイントとの統合
