# Playable Vertical Slice (統合ランナー)

## 概要

Battle / Quest / Save の既存 Vertical Slice を統合し、プレイヤー視点で最小進行を一連で確認できる CLI ランナーを追加した。

- タイトル導線: New Game / Continue / Exit
- 拠点メニュー: 状態確認、所持品確認、アイテム使用、装備変更、ショップ、宿屋、NPC会話、討伐、報告、セーブ、ロード、終了
- 進行ループ: 受注 → 戦闘 → 報告 → 完了

## 実行方法

```bash
python -m game.app.cli.run_game_slice
```

任意の保存先を使う場合:

```bash
python -m game.app.cli.run_game_slice --save-path tmp/playable_slice_slot_02.json
```

## 確認フロー（最短）

1. `New Game` を選ぶ
2. `NPCと話す（受注）` を選ぶ
3. 勝利時は `報告する` が表示されるので選ぶ
4. `ショップに行く` で装備/消耗品を購入する
5. `宿屋に泊まる` で gold 消費と全体回復を確認する
6. `装備変更` で武器/防具を装着してステータス更新を確認する
7. `セーブする` を選ぶ
8. `終了する` でタイトルへ戻る
9. `Continue / Load` で再開し、`ステータス確認` で状態保持を確認する

※ 敗北時は `討伐へ進む` が表示され、再戦して進行できる。

## 接続方針

- Quest 進行は `QuestSliceSession` を利用し、イベント実行と状態遷移をそのまま再利用
- 戦闘起動は既存 `build_battle_executor` で Battle Session を呼び出す
- セーブ/ロードは `SaveSliceApplicationService` と `JsonFileSaveRepository` を利用
- ショップ/購入は `ShopMasterDataRepository` と `ShopService` を利用
- 統合層はオーケストレーションに限定し、Battle / Quest / Save の内部実装詳細へ依存しない

## 今回のスコープ外

- GUI
- 複数セーブスロットの完成版
- 複数クエスト同時管理の完成版
- 本格ショップ / 装備UI
- 高度なエラーハンドリング

## 次の拡張ポイント

- 章ごとのハブ遷移と複数クエスト導線
- バトル結果の詳細反映（HP/SP消耗の永続化）
- セーブスロット管理の導入
- スクリプトイベント分岐（フラグ条件による会話差分）
