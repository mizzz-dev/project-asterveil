from __future__ import annotations

import json
from pathlib import Path

from game.save.domain.entities import SaveData


class JsonFileSaveRepository:
    def __init__(self, save_file_path: Path) -> None:
        self._save_file_path = save_file_path

    def save(self, save_data: SaveData) -> None:
        self._save_file_path.parent.mkdir(parents=True, exist_ok=True)
        payload = save_data.to_dict()
        self._save_file_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self) -> SaveData:
        raw = json.loads(self._save_file_path.read_text(encoding="utf-8"))
        return SaveData.from_dict(raw)


class InMemorySaveRepository:
    def __init__(self) -> None:
        self._payload: dict | None = None

    def save(self, save_data: SaveData) -> None:
        self._payload = save_data.to_dict()

    def load(self) -> SaveData:
        if self._payload is None:
            raise ValueError("save_data not found")
        return SaveData.from_dict(self._payload)
