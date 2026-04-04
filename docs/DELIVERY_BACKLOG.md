# Delivery Backlog (Must / Should / Could)

本書は、`DESIGN_PROPOSAL_JRPG.md` の機能群を実装優先度と依存関係で再構造化した実行バックログである。

## 1) 優先度ルール

- **Must**: 6か月Go判断とMVP成立に必須。未達ならスコープ縮小してでも実施。
- **Should**: MVP品質を底上げする。遅延時はフェーズ後半へ移動。
- **Could**: 将来拡張。MVP期間では原則着手しない。

## 2) Epic一覧

| Epic | 目的 | MoSCoW | 優先度 | 主依存 |
|---|---|---|---|---|
| Core Battle | 戦闘コア成立（弱点/ブレイク/連携） | Must | P0 | UI/UX Foundations, Save/Data |
| Narrative Pipeline | 章実装の再現可能な制作フロー確立 | Must | P0 | Content Authoring Pipeline |
| World / Quest Framework | 探索とクエスト進行の骨格実装 | Must | P0 | Narrative Pipeline, Save/Data |
| Character Progression | レベル/装備/星紋ボード最小ループ | Must | P0 | Core Battle |
| Save / Data | セーブ堅牢性とデータ駆動基盤 | Must | P0 | Platform Readiness |
| UI / UX Foundations | PC/モバイル両対応の基本UX | Must | P0 | Core Battle |
| Content Authoring Pipeline | シナリオ/クエスト/バトルデータ量産 | Must | P1 | Save/Data |
| Multiplayer Foundations | 協力試験版1種の成立 | Should | P1 | Core Battle, Platform Readiness |
| Telemetry / LiveOps Foundations | KPI計測と運営基礎導線 | Should | P1 | Save/Data, Platform Readiness |
| Platform Readiness | Steam優先 + モバイル適用性検証 | Must | P0 | UI/UX Foundations |

## 3) Epic詳細（issue分解の起点）

### 3.1 Core Battle
- **目的**: CTB戦闘の中核をMVP品質で成立。
- **完了条件**:
  - 弱点/ブレイク/連携が3章分の敵で機能する。
  - 難易度3段階が動作し、章1の戦闘離脱率が閾値内。
- **リスク**: 複雑化による離脱率増加。
- **子タスク例**:
  1. CTB行動順計算モジュール（Weight反映）
  2. 弱点判定テーブル実装（属性+武器）
  3. 予兆UI連動（次ターン危険行動表示）
  4. 戦闘リザルトのテレメトリ発火

### 3.2 Narrative Pipeline
- **目的**: 章制作を属人化させず反復可能にする。
- **完了条件**:
  - 章テンプレ（導入/中盤/山場/締め）で章1〜3を実装。
  - 分岐整合チェック手順が定義され、QA受け入れ済み。
- **リスク**: 執筆遅延、演出要求肥大化。
- **子タスク例**:
  1. シーンID規約策定
  2. 章進行フラグ表作成
  3. 感情ピーク演出チェックリスト化

### 3.3 World / Quest Framework
- **目的**: メイン・サブ・個別クエストを同一基盤で進行。
- **完了条件**:
  - クエスト5類型（提案書準拠）を最低1件ずつ実装。
  - 進行不能バグゼロで章3まで通し動作。
- **リスク**: クエスト分岐とNPC状態遷移の破綻。
- **子タスク例**:
  1. クエスト状態遷移（未受注/進行中/完了）
  2. ハブUIの推薦導線
  3. クリア後世界変化フック（台詞/配置）

### 3.4 Character Progression
- **目的**: 育成の選択価値を初期段階で提供。
- **完了条件**:
  - Lv成長、装備、星紋ボード簡易版が章3まで機能。
  - 推奨装備提案（ライト向け）が利用可能。
- **リスク**: 育成導線不明瞭による詰まり。
- **子タスク例**:
  1. ステータス計算式定義
  2. 装備OP範囲固定テーブル実装
  3. 素材逆引きUI導線

### 3.5 Save / Data
- **目的**: 進行資産を壊さず安全に更新できる基盤を構築。
- **完了条件**:
  - オート3/手動10セーブ、CRC検証、世代復旧が動作。
  - マスターデータ更新時の互換性ルールが文書化。
- **リスク**: バージョン差分による破損。
- **子タスク例**:
  1. セーブフォーマットv1策定
  2. 破損時リカバリフロー実装
  3. データバージョニングCIチェック

### 3.6 UI / UX Foundations
- **目的**: 情報量が多くても迷わない戦闘/探索UIを成立。
- **完了条件**:
  - 戦闘HUD、編成、クエスト導線がPC/モバイルで可用。
  - コマンド階層2段原則を維持。
- **リスク**: モバイル視認性・操作回数の増加。
- **子タスク例**:
  1. 行動順タイムライン固定表示
  2. 長押し詳細UI
  3. チュートリアル導線AB比較

### 3.7 Content Authoring Pipeline
- **目的**: コンテンツ量産の工数を可視化・圧縮。
- **完了条件**:
  - シナリオ/クエスト/敵データの入力テンプレとレビュー手順がある。
  - 新規サブクエ追加が1日以内で可能。
- **リスク**: ツール不足による手作業増大。
- **子タスク例**:
  1. クエスト記述テンプレ
  2. バトル敵設定シート
  3. データ投入→ビルド反映の自動化

### 3.8 Multiplayer Foundations
- **目的**: 本編を阻害しない協力試験版を成立。
- **完了条件**:
  - 2〜4人協力の1コンテンツを実装し、切断復帰テスト合格。
  - 限定報酬が時短/外装中心であることを確認。
- **リスク**: 同期不具合、不正対策未整備。
- **子タスク例**:
  1. ルーム作成/参加
  2. ターン確定同期
  3. 最低限のチート検知ログ

### 3.9 Telemetry / LiveOps Foundations
- **目的**: 難易度/離脱分析を可能にし、運営の意思決定を早める。
- **完了条件**:
  - KPIイベント（章進行、全滅、離脱、再挑戦）を収集。
  - ダッシュボードで週次確認可能。
- **リスク**: 計測漏れで判断不能。
- **子タスク例**:
  1. イベント命名規約
  2. 章別ファネル可視化
  3. Go/No-Go用レポート雛形

### 3.10 Platform Readiness
- **目的**: Steam先行開発とモバイル展開可能性の同時担保。
- **完了条件**:
  - Steam体験版準備要件を満たす。
  - モバイル中位端末で最低性能基準を満たす。
- **リスク**: 最適化遅延、入力差異によるUX劣化。
- **子タスク例**:
  1. 入力デバイス差分テスト
  2. 30fps省電力モード検証
  3. パッチ配信手順の検証

## 4) 依存関係と優先順位（実行順）

1. Save / Data（基盤）
2. Core Battle + UI / UX Foundations（体験コア）
3. Narrative Pipeline + World / Quest Framework（章体験）
4. Character Progression + Content Authoring Pipeline（量産性）
5. Platform Readiness + Telemetry（判断可能性）
6. Multiplayer Foundations（Should範囲で検証）

## 5) スコープ調整ルール（遅延時）

- **削減優先**: Could → Should → Mustの順。
- **禁止事項**: Must内の品質要件（進行不能0、セーブ堅牢性）を削らない。
- **条件付き延期**: Multiplayer FoundationsはM6直前で未達なら正式実装を後続フェーズへ移行。

## 6) Sprint ticketに直結する粒度例

- Epic: Core Battle
  - Story: 「プレイヤーとして、敵の危険行動を事前に知りたい。対策を選びたいから。」
  - AC1: 敵の大技前に予兆アイコンが1ターン前表示される。
  - AC2: 予兆未表示の致死級行動はMVP範囲で禁止。
  - AC3: 戦闘ログに予兆発生イベントが記録される。

