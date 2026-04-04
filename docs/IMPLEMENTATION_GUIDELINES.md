# IMPLEMENTATION GUIDELINES (Vertical Slice Start)

## 1. 実装ルール

- まず Domain の契約（入力/出力）を定義してからUIを作る。
- 1機能1責務を徹底し、巨大クラス化を避ける。
- 仕様が曖昧な箇所は `docs/` に先に合意メモを残す。

## 2. 命名規約

- クラス/型: `PascalCase`
- 関数/変数: `camelCase`
- 定数: `UPPER_SNAKE_CASE`
- データID: `lower_snake` + ドット区切り（`quest.ch01.xxx`）
- ブランチ/チケット: `feature/<epic>-<short-topic>`

## 3. ディレクトリ規約

- `game/`: ゲーム実装コード（将来のエンジン実体）
- `data/`: マスター/セーブ契約/サンプル定義
- `tools/`: データ検証・変換・補助スクリプト
- `tests/`: ドメイン/結合テスト、テストフィクスチャ
- `prototypes/`: 実験用。採用時は正式ディレクトリへ昇格

## 4. 依存方向ルール

- Domain は他レイヤーを import しない。
- UI から Infrastructure への直接アクセス禁止。
- Save I/O は Application 経由で呼び出す。

## 5. UI実装ルール

- 2階層以内コマンド原則を維持。
- 予兆・弱点・行動順は同時視認できる配置を優先。
- UIは表示責務のみ。判定はUseCase/Domainへ委譲。

## 6. データアクセス方針

- マスターは Repository 経由で取得。
- 画面ごとの ad-hoc ロードは禁止し、セッション単位で再利用。
- マスター更新時はバリデーションをCIで実行。

## 7. ログ / エラー方針

- ログレベル: `DEBUG/INFO/WARN/ERROR` を統一。
- プレイ継続不能は `ERROR` + 復旧導線（タイトル帰還/再読込）を必須。
- 期待される分岐失敗（例: クエスト未達）は `WARN` 扱い。

## 8. Feature追加時の手順

1. 対応Epicと受け入れ条件を `docs/DELIVERY_BACKLOG.md` に紐付け
2. `docs/CONTENT_SCHEMA.md` への契約影響を確認
3. Domainユースケース追加
4. Application接続
5. UI接続
6. テスト追加（正常/異常/境界）
7. テレメトリイベント追加（必要時）

## 9. issue化しやすい分割例

- 例: 「章1ボス戦」
  - issue-1: boss定義データ作成
  - issue-2: 予兆UI表示
  - issue-3: ブレイク閾値調整
  - issue-4: 戦闘終了→章進行接続
  - issue-5: QAケース（全滅/再挑戦/勝利）

## 10. レビュー時の確認観点

- 責務分離が崩れていないか
- 既存ID・セーブ互換性に影響していないか
- MVPスコープ外機能を混入していないか
- テスト観点（正常/異常/境界）が揃っているか
- ドキュメント更新と実装が一致しているか
