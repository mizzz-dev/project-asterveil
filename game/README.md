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
