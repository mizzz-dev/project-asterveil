# GATHERING_VERTICAL_SLICE

## 概要

本スライスは、ロケーション依存の採取ポイントから素材を入手し、既存の所持品/クラフト導線へ接続する最小実装を定義する。

- マスターデータ: `data/master/gathering_nodes.sample.json`
- ランタイム状態: `gathered_node_ids`（採取済みノードID集合）
- 対象導線: `PlayableSliceApplication` の現在地確認 / 採取 / 所持品 / クラフト / セーブ&ロード

## 対応範囲（今回）

- ロケーションごとの採取ポイント一覧表示
- ノード単位の採取可否判定
  - 現在地一致
  - `unlock_flags` 充足
  - `repeatable=false` かつ採取済みなら再採取不可
- 採取結果（loot）解決と inventory 反映の責務分離
- Save/Load で採取済みノード状態を保持
- `respawn_rule` による最小リポップ
  - `on_rest`: 宿屋宿泊で再採取可能
  - `on_return_to_hub`: 拠点帰還で再採取可能
  - `none`: 非リポップ（従来どおり一度きり）

## 非対応（今回スコープ外）

- 時間経過リポップ
- 採取ツール耐久/消耗
- レア演出/ミニゲーム
- 大量一括採取
- 天候/時間帯依存

## 実行方法

```bash
python -m game.app.cli.run_game_slice
```

ゲーム開始後、拠点メニューの `採取ポイント確認` と `採取する` を使用する。

## 拡張ポイント

- `repeatable=true` ノードの再採取制御（クールダウン/日次リセット）
- quest objective と採取ノードの直接連携
- 採取結果に quality / rarity / bonus table を追加
- 採取専用パッシブや装備との連携
