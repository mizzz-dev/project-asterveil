from __future__ import annotations

import argparse
from pathlib import Path

from game.app.application.playable_slice import PlayableSliceApplication


def _choose(items: list[tuple[str, str]]) -> str:
    for idx, (_, label) in enumerate(items, start=1):
        print(f"{idx}. {label}")

    while True:
        raw = input("選択してください: ").strip()
        if not raw.isdigit():
            print("数字を入力してください。")
            continue
        index = int(raw)
        if index < 1 or index > len(items):
            print("範囲外です。")
            continue
        return items[index - 1][0]


def _run_use_item_flow(app: PlayableSliceApplication) -> list[str]:
    item_ids = app.usable_item_ids()
    if not item_ids:
        return ["usable_item:none"]

    item_choices = []
    for item_id in item_ids:
        amount = app.inventory_state.get("items", {}).get(item_id, 0)
        item_choices.append((item_id, f"{item_id} x{amount}"))
    selected_item_id = _choose(item_choices)

    member_choices = []
    for member_line in app.party_member_lines():
        parts = member_line.split(":")
        character_id = parts[1]
        member_choices.append((character_id, member_line))
    selected_target = _choose(member_choices)

    return app.use_item(selected_item_id, selected_target)


def _run_shop_flow(app: PlayableSliceApplication) -> list[str]:
    catalog = app.shop_catalog_lines()
    for line in catalog:
        print(f"- {line}")
    if any(line.startswith("shop_failed:") for line in catalog):
        return []

    purchase_choices = [("cancel", "購入しない")]
    for line in catalog:
        if not line.startswith("shop_item:"):
            continue
        _, item_id, item_name, price_part, _ = line.split(":", 4)
        purchase_choices.append((item_id, f"{item_name} ({item_id}) {price_part}"))

    selected_item = _choose(purchase_choices)
    if selected_item == "cancel":
        return ["shop_purchase_cancelled"]
    return app.buy_item(selected_item)


def run_playable_vertical_slice(save_path: Path) -> int:
    app = PlayableSliceApplication(master_root=Path("data/master"), save_file_path=save_path)

    while True:
        print("\n=== Project Asterveil: Playable Vertical Slice ===")
        top_choice = _choose(
            [
                ("new", "New Game"),
                ("continue", "Continue / Load"),
                ("exit", "Exit"),
            ]
        )

        if top_choice == "exit":
            print("ゲームを終了します。")
            return 0
        if top_choice == "new":
            for log in app.new_game():
                print(f"- {log}")
        else:
            ok, message = app.continue_game()
            print(f"- {message}")
            if not ok:
                continue

        while True:
            print("\n--- 拠点メニュー ---")
            actions = [(item.key, item.label) for item in app.available_actions()]
            selected = _choose(actions)
            if selected == "use_item":
                logs = _run_use_item_flow(app)
            elif selected == "shop":
                logs = _run_shop_flow(app)
            else:
                logs = app.perform_action(selected)
            for log in logs:
                print(f"- {log}")
            if selected == "exit":
                break


def main() -> int:
    parser = argparse.ArgumentParser(description="最小プレイアブルVertical Sliceランナー")
    parser.add_argument("--save-path", default="tmp/playable_slice_slot_01.json", help="セーブファイルパス")
    args = parser.parse_args()
    return run_playable_vertical_slice(Path(args.save_path))


if __name__ == "__main__":
    raise SystemExit(main())
