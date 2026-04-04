# TECHNICAL FOUNDATION (Vertical Slice Bootstrap)

## 1. 技術的目的

Project Asterveil の Vertical Slice 実装では、次を最優先にする。

1. **体験の再現性**: 1章分の探索→会話→戦闘→ボス→クリアが安定して繰り返し作れること。
2. **責務分離**: バトル・クエスト・セーブ・UI・データを独立に改善できること。
3. **データ駆動**: 章追加・敵追加・クエスト追加をコード改修最小で行えること。
4. **将来拡張性**: 協力プレイ・LiveOpsを想定しつつ、MVP期間は単体プレイ品質を損なわないこと。

本方針は `DESIGN_PROPOSAL_JRPG.md` の「ソロ主軸 + 協力補助」と、`docs/MVP_EXECUTION_PLAN.md` の Vertical Slice 定義に整合させる。

---

## 2. Vertical Slice で必要な最小技術範囲

- **Gameplay Core**
  - CTB行動順 (SPD + Weight)
  - 弱点 / ブレイク / スタン / 連携の最小成立
  - クエスト状態遷移 (未受注/進行中/完了)
- **Progression Core**
  - キャラクター成長（Lv、装備、最小ビルド）
- **Persistence Core**
  - セーブ/ロード、スロット管理、バージョン管理、破損対策
- **Presentation Core**
  - 戦闘HUD、行動順UI、クエスト導線UI、会話進行UI
- **Data/Tooling Core**
  - マスターデータ定義、検証ルール、データ投入手順

---

## 3. 推奨レイヤー構成

```text
[Presentation]
  UI / Input / Scene Flow / VFX Trigger
      ↓ (calls)
[Application]
  UseCase / Orchestrator / Session State
      ↓ (uses)
[Domain]
  Battle Rules / Quest Rules / Progression Rules
      ↓ (interfaces)
[Infrastructure]
  Save I/O / Data Repository / Telemetry / Platform Adapter
```

### 3.1 各レイヤー責務

- **Presentation**
  - 画面表示・入力解釈・演出トリガーのみ。ゲームルールを持たない。
- **Application**
  - 画面やイベントをまたぐ進行制御（章遷移、戦闘開始、報酬反映）。
- **Domain**
  - 純粋ルール（ダメージ、状態異常、勝敗条件、クエスト完了条件）。
- **Infrastructure**
  - ファイル保存、外部サービス、計測、将来の通信接続。

依存方向は **Presentation → Application → Domain ← Infrastructure** を維持し、Domain は外部依存を持たない。

---

## 4. 機能別の責務分離

## 4.1 Battle
- Domain: 行動順計算、弱点判定、ブレイク値、状態異常、勝敗判定
- Application: バトルセッション開始/終了、報酬反映、リトライ遷移
- Presentation: コマンドUI、タイムライン表示、予兆表示

## 4.2 Quest
- Domain: クエスト状態機械、目標達成判定
- Application: 受注/更新/完了処理、章進行との同期
- Presentation: クエストログ、ナビ導線、完了演出

## 4.3 Save
- Domain: 保存対象構造（進行状態の意味）
- Infrastructure: シリアライズ、CRC、世代復旧、バージョン移行
- Application: セーブタイミングの制御（戦闘後・章遷移等）

## 4.4 UI
- Presentation 専任。Domainロジック直接参照禁止。
- Application DTO を表示する。

## 4.5 Data Management
- Infrastructure: マスター読込、キャッシュ、バリデーション
- Domain: マスターを参照して計算するが、直接I/Oしない

---

## 5. 将来マルチ対応を見据えた境界設計

- `Domain` は「決定的な入力→結果」を返す純粋計算を基本にする。
- `Application` ではコマンド処理を `PlayerAction` 単位で扱い、将来 `RemoteAction` を同形で扱えるようにする。
- `Infrastructure` に `SessionGateway` 境界を置き、初期は Local 実装のみ提供する。

### 同期実装を今すぐ入れない場合の方針

- ネットワークコードは実装しない。
- 代わりに境界インターフェースのみ定義し、Local loopback 実装で Vertical Slice を進める。
- 協力試験版は後続フェーズで `SessionGateway` の差し替えで対応する。

---

## 6. データ駆動設計の基本方針

- コンテンツ（キャラ/敵/スキル/クエスト/会話）は **ID参照** で接続する。
- ルールコードは汎用化し、バランス値・条件式・テキストはマスターへ寄せる。
- 章テンプレート・クエストテンプレートを使い、量産時の差分を限定する。

### 設定値・マスターデータ・実行時状態の分離

- **Settings**: 環境依存/調整定数（難易度係数、初期所持金など）
- **Master Data**: 静的定義（敵ステータス、スキル効果、クエスト条件）
- **Runtime State**: プレイヤー進行（現在HP、進行フラグ、クリア履歴）

---

## 7. イベント/シナリオ進行方針

- シーンID・イベントID・フラグIDを分離する。
- 会話進行は `ConversationDefinition`（静的）と `ConversationState`（実行時）を分離する。
- 章進行は「必須イベント完了集合」で判定し、単一巨大フラグに依存しない。

---

## 8. テストしやすい構造の原則

- Domainは副作用なしでユニットテスト可能にする。
- Applicationはユースケース単位の結合テストを行う。
- Save互換テスト（vN→vN+1）を固定フィクスチャで維持する。
- UIはスナップショット/操作導線テストを最小導入する。

---

## 9. 初期実装で避けるべきアンチパターン

1. UIから直接セーブファイルを書き換える。
2. 1つの巨大Managerに戦闘・クエスト・セーブ責務を集約する。
3. ID文字列をハードコード散在させる。
4. マスターデータ更新時に互換性ルールを持たない。
5. テスト不能な乱数・時刻依存をDomainへ直書きする。

---

## 10. Vertical Slice 開始チェックリスト

- [ ] レイヤー責務をチーム内で合意した
- [ ] ID命名規約とデータ契約を合意した
- [ ] セーブ対象と非対象を明文化した
- [ ] 章1の進行フラグ表を作成した
- [ ] バトル/クエストの最小テストケースを用意した
