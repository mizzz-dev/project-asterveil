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
