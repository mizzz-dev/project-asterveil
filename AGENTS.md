# AGENTS.md

このファイルは、Project Asterveil リポジトリで Codex / 開発者が一貫した方針で安全に作業するための実務ガイドです。詳細仕様は `docs/` 配下の原本を参照し、本書は「作業時の判断基準」に集中します。

## 1. プロジェクトの目的と前提

- 本プロジェクトは、長編ストーリー型のコマンドバトルRPGを段階的に実装する取り組みです。
- 現在フェーズは、Vertical Slice / MVP を積み上げる段階です。
- 方針は「大規模一括実装」より「小さく安全な増分実装」を優先します。
- データ駆動（`data/master` / `data/save_contract`）と責務分離（`domain` / `application` / `infrastructure` / `cli`）を最重要原則とします。

## 2. 作業前に確認すべき資料（優先順）

最低限、着手前に以下を確認してください。

1. 全体設計
   - `DESIGN_PROPOSAL_JRPG.md`
2. MVP計画・優先度
   - `docs/MVP_EXECUTION_PLAN.md`
   - `docs/DELIVERY_BACKLOG.md`
   - `docs/MILESTONE_ROADMAP.md`
3. 技術基盤・実装原則
   - `docs/TECHNICAL_FOUNDATION.md`
   - `docs/IMPLEMENTATION_GUIDELINES.md`
4. データ契約
   - `docs/CONTENT_SCHEMA.md`
   - `data/save_contract/save_data_v1.sample.json`
5. 対象機能の Vertical Slice 資料
   - 例: `docs/BATTLE_VERTICAL_SLICE.md`, `docs/QUEST_VERTICAL_SLICE.md`, `docs/PLAYABLE_VERTICAL_SLICE.md` など

## 3. リポジトリの基本理解

- `game/`: ゲーム実装本体
  - `battle`: 戦闘ルール/セッション進行
  - `quest`: クエスト状態遷移・進行
  - `save`: セーブ契約・保存/復元
  - `app`: playable slice の統合導線（battle/quest/save/shop/equipment/inn/dialogue 連携）
  - `location`: 移動・ロケーション遷移
  - `shop`: 購入処理と店舗データ利用
- `data/`:
  - `master/*.sample.json`: 静的なマスターデータ（定義データ）
  - `save_contract/save_data_v1.sample.json`: セーブ契約サンプル
- `docs/`: 設計・計画・Vertical Slice仕様
- `tests/`: `unittest` ベースの自動テスト
- `prototypes/`: 実験実装（採用時に正式ディレクトリへ移管）

### master data と runtime state の違い

- master data: 作品定義として静的に管理するデータ（敵/スキル/クエスト等）
- runtime state: プレイ中に変化する状態（HP, quest_state, inventory_state 等）
- 実装上、この2つを同じ責務・同じ保存先で混在させないこと。

### save contract の扱い

- `save_data_v1` は互換性を伴う契約です。
- 既存キーの意味変更・削除は原則禁止。必要時はバージョン更新と移行方針をセットで検討します。

## 4. 実装時の基本原則

- 既存の責務境界を壊さない（特に `battle` / `quest` / `save` / `app` の分離）。
- 変更は小さく保つ（1PR1目的を基本）。
- 完成版を一気に目指さず、最小の Vertical Slice 成立を優先する。
- 既存のデータ駆動方針を尊重する（新規定義は原則 `data/master` へ）。
- ハードコードは暫定用途に限定し、恒久仕様はデータ定義へ移す。
- master data と runtime state を混ぜない。
- 既存 CLI / unittest の流れを壊さず再利用する。

## 5. 変更時の優先順位

1. 既存実装の再利用（関数・サービス・リポジトリ）
2. 最小限の新規追加（必要な差分のみ）
3. 大きな設計変更（最後の手段）

併せて以下を厳守:

- 無関係なリファクタリングを同一PRに混ぜない
- 不要なファイル移動・命名変更を避ける

## 6. データ変更ルール

### `data/master/*.sample.json` を更新する場合

- `docs/CONTENT_SCHEMA.md` のID規約・必須項目と一致させる。
- 参照IDの整合性（存在チェック）を崩さない。
- 既存IDはリネームせず、追加/非推奨で扱う。
- 変更対象機能（battle/quest/shop等）の実装・テストと同時に更新する。

### `data/save_contract/save_data_v1.sample.json` を更新する場合

- save contract の互換性影響を明記する。
- スキーマ変更時は、読み込み側実装・テスト・関連 docs を同時更新する。
- フィールド削除や意味変更は慎重に扱い、必要ならバージョン更新を検討する。

### 共通ルール

- スキーマと実装の乖離を作らない。
- ID命名規則（`<category>.<group>.<name>`）を維持する。
- データ不備時には最低限の失敗検知（例外/バリデーション/テスト）を用意する。

## 7. テストルール

- 変更時は既存 `unittest` を壊さないこと。
- 新機能・仕様変更には対応テストを追加すること。
- ドキュメントのみ変更時は「ドキュメント変更のみ」を明記すること。
- CLI導線に関わる変更は必要に応じて手動確認観点も記載すること。

実行例:

- `python -m unittest`
- `python -m unittest tests.test_playable_slice`
- `python -m game.app.cli.run_game_slice`（手動確認）

## 8. PR / コミット / 最終報告ルール（必須）

このプロジェクトでは以下を必須とします。

- **PRタイトルは日本語**
- **PR本文は日本語**
- **コミットメッセージは日本語**
- **最終報告は日本語**

PR本文テンプレート:

```md
### 動機
- 変更の必要性

### 変更内容
- 何をどう変更したか

### テスト
- 実施した確認内容
- 未実施なら理由
```

追加ルール:

- テスト未実施時は、理由を日本語で明記する。
- 最終報告には追加・更新ファイル一覧を含める。
- 最終報告には今回のスコープ外も明記する。

## 9. Codex向け具体的行動ルール

- まず関連ファイル・関連docsを読んでから編集する。
- 既存実装パターン（層分離・命名・データ参照方法）を踏襲する。
- 既存命名・責務分離に合わせる。
- 迷ったら「最小差分で成立する案」を選ぶ。
- ユーザーが明示していない大規模拡張を勝手に入れない。
- テスト追加/更新と docs 更新の要否を毎回確認する。
- 変更理由を説明できないコードは入れない。

## 10. このプロジェクトで避けるべきこと

- 責務の跨ぎすぎ（1モジュールへの過集中）
- `save` / `quest` / `battle` の密結合
- データ定義なしの場当たり的ハードコード
- 一度に大きすぎる機能追加
- 無関係なリファクタリング
- 英語PR / 英語コミット
- テストなしのロジック変更
- docs 更新漏れ
- save contract を無自覚に壊す変更

## 11. 推奨作業フロー

1. 依頼内容の整理（目的・制約・完了条件）
2. 関連ドキュメント確認（本書 2章の優先順）
3. 影響範囲確認（コード/データ/テスト/docs）
4. 最小設計（差分最小で成立する設計）
5. 実装（責務境界を維持）
6. テスト追加/更新（必要な自動・手動確認）
7. README / docs 更新（必要時のみ）
8. 日本語でコミット・日本語でPR作成

## 12. 変更規模の判断基準

### 小変更で済むケース

- 既存ドメイン内の軽微なロジック修正
- 既存データへの項目追加（互換影響がない）
- テスト追加のみ / docs補足のみ

### 新規ドメイン追加が必要なケース

- `battle` / `quest` / `save` / `app` の既存責務で説明不能な新責務が恒常的に必要
- 今後の反復実装で再利用される独立概念がある

### save contract 更新が必要なケース

- ランタイム状態として永続化すべき情報が増え、既存契約で表現不能
- 復元時のゲーム挙動が新規フィールドに依存する

### docs のみで済むケース

- 実装挙動は変えず、運用手順・仕様説明・判断基準の明確化のみ行う場合

---

必要に応じて、各機能の詳細仕様は `docs/*_VERTICAL_SLICE.md` と `docs/IMPLEMENTATION_GUIDELINES.md` を正としてください。
