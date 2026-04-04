# game/

ゲーム実装コードを配置するルート。

- 目的: Vertical Slice 以降の本体実装を段階的に追加する。
- 方針: `docs/TECHNICAL_FOUNDATION.md` のレイヤー責務に従って構成する。
- 注意: プロトタイプコードは原則 `prototypes/` に置き、採用時に移動する。

## battle/

最小戦闘コア実装。

- `game/battle/domain/`: 戦闘ルール（HP更新・行動順・勝敗判定）
- `game/battle/application/`: セッション進行（ターン/ラウンド進行）
- `game/battle/infrastructure/`: マスターデータ読み込み
- `game/battle/cli/`: 開発者確認用ランナー

詳細は `docs/BATTLE_VERTICAL_SLICE.md` を参照。


## quest/

会話イベント + クエスト最小進行実装。

- `game/quest/domain/`: クエスト状態機械、イベント/戦闘結果契約
- `game/quest/application/`: イベント進行オーケストレーション
- `game/quest/infrastructure/`: クエスト/イベントマスターデータ読込
- `game/quest/cli/`: Vertical Slice確認ランナー

詳細は `docs/QUEST_VERTICAL_SLICE.md` を参照。


## save/

Vertical Slice向けの最小セーブ/ロード実装。

- `game/save/domain/`: セーブ契約モデルと整合チェック
- `game/save/application/`: Quest Sessionとの相互変換
- `game/save/infrastructure/`: JSONファイル保存 / インメモリ保存
- `game/save/cli/`: セーブ→ロード→進行継続の確認ランナー

詳細は `docs/SAVE_VERTICAL_SLICE.md` を参照。


## app/

Vertical Slice 統合ランナー実装。

- `game/app/application/`: タイトル導線・ハブメニュー・Battle/Quest/Save連携のオーケストレーション
- `game/app/cli/`: 最小プレイアブル体験を確認する CLI エントリーポイント
- `game/app/infrastructure/`: Playable Slice 向けマスターデータ読込（報酬・アイテム）
- `game/shop/domain|infrastructure/`: ショップ定義/購入処理とマスターデータ読込

実行例: `python -m game.app.cli.run_game_slice`

報酬/成長/所持品の詳細は `docs/PROGRESSION_VERTICAL_SLICE.md` を参照。

パーティ状態確認と消耗品使用の最小ループは `docs/PARTY_MENU_VERTICAL_SLICE.md` を参照。

ショップ/購入フローの最小ループは `docs/SHOP_VERTICAL_SLICE.md` を参照。
