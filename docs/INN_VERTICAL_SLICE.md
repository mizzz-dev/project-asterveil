# Inn Vertical Slice（宿屋 / 休息）

## 概要

Playable Slice の拠点メニューに、最小の宿屋ループを追加した。

- 宿屋マスターデータ（料金・説明・復帰ポリシー）
- 宿泊可否判定（宿屋ID・所持金・パーティ状態）
- 宿泊実行（gold消費、全体HP/SP全回復、戦闘不能復帰）
- Save / Load での状態保持

今回の目的は「出撃前にパーティを立て直せる最小体験」を成立させることであり、宿泊演出や時間経過は対象外。

## 実装内容

### 1) 宿屋定義（静的データ）

- `data/master/inns.sample.json` を追加。
- 最小項目:
  - `inn_id`
  - `name`
  - `stay_price`
  - `description`
  - `revive_knocked_out_members`
  - `location_id`（任意）

マスターデータは「何をいくらで提供するか」のみを持ち、所持金や現在HP/SPは保存データ側に持たせる。

### 2) 宿屋サービス（ランタイム処理）

- `InnService` を追加し、以下を担当:
  - 宿屋IDの存在確認
  - 所持金チェック
  - パーティ状態の最小妥当性チェック
  - 宿泊反映

### 3) 回復/復帰仕様（今回の最小仕様）

- `revive_knocked_out_members=true` の宿屋では、宿泊時に全メンバーの `alive` を `True` にする。
- その後、各メンバーの `current_hp/current_sp` を回復。
- 回復上限は `EquipmentService.resolve_final_stats` を通し、装備補正込み `max_hp/max_sp` を使用する。
  - これにより、装備で上限が増えた状態でも正しい全回復になる。

## Playable Slice との接続

- 拠点メニューに `宿屋に泊まる` を追加。
- 宿屋フロー:
  1. 宿屋情報（料金・所持金・復帰ポリシー）を表示
  2. 宿泊可否を判定
  3. 成功時は宿泊結果 + メンバーステータスを表示
  4. 失敗時は理由コードを表示

## Save / Load との整合

既存の保存契約で `party_state.members[*].current_hp/current_sp/alive` と `inventory_state.gold` を保持しているため、
宿屋対応で保存契約の追加変更は行っていない。

## 実行方法

```bash
python -m game.app.cli.run_game_slice
```

## 今回のスコープ外

- 宿泊イベント会話
- 時間経過
- 割引・宿ランク差
- バフ付き宿泊
- 複数宿屋UI
- 状態異常の完成版回復

## 次の拡張ポイント

- 章/地域ごとの複数宿屋と料金差
- フラグ条件による割引・無料宿泊
- 宿泊会話/イベント再生
- 状態異常回復ポリシー（宿屋ごとの差異）
- 時間経過/日数管理との接続
