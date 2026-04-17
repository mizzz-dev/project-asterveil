from __future__ import annotations

import json
from pathlib import Path

from game.app.application.equipment_salvage_service import EquipmentSalvageDefinition, SalvageReturnItem


class EquipmentSalvageMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load(self, *, valid_equipment_ids: set[str], valid_item_ids: set[str]) -> dict[str, EquipmentSalvageDefinition]:
        path = self._root / "equipment_salvage.sample.json"
        raw = json.loads(path.read_text(encoding="utf-8"))

        definitions: dict[str, EquipmentSalvageDefinition] = {}
        for row in raw:
            equipment_id = str(row.get("equipment_id") or "")
            if not equipment_id:
                raise ValueError("equipment_salvage.sample.json missing field=equipment_id")
            if equipment_id not in valid_equipment_ids:
                raise ValueError(f"equipment_salvage.sample.json unknown equipment_id={equipment_id}")

            base_returns = self._load_returns(
                row.get("base_returns", []),
                valid_item_ids=valid_item_ids,
                source=f"equipment_id={equipment_id}:base_returns",
            )
            upgrade_bonus_returns = self._load_returns(
                row.get("upgrade_bonus_returns", []),
                valid_item_ids=valid_item_ids,
                source=f"equipment_id={equipment_id}:upgrade_bonus_returns",
            )

            definitions[equipment_id] = EquipmentSalvageDefinition(
                equipment_id=equipment_id,
                salvage_enabled=bool(row.get("salvage_enabled", False)),
                required_workshop_level=max(1, int(row.get("required_workshop_level", 1))),
                base_returns=base_returns,
                upgrade_bonus_returns=upgrade_bonus_returns,
                salvage_tags=tuple(str(tag) for tag in row.get("salvage_tags", [])),
                description=str(row.get("description", "")),
            )

        return definitions

    def _load_returns(
        self,
        rows: list[dict],
        *,
        valid_item_ids: set[str],
        source: str,
    ) -> tuple[SalvageReturnItem, ...]:
        returns: list[SalvageReturnItem] = []
        for row in rows:
            item_id = str(row.get("item_id") or "")
            quantity = int(row.get("quantity", 0))
            if item_id not in valid_item_ids:
                raise ValueError(f"equipment_salvage.sample.json unknown item_id={item_id} source={source}")
            if quantity <= 0:
                raise ValueError(f"equipment_salvage.sample.json quantity must be >0 item_id={item_id} source={source}")
            returns.append(SalvageReturnItem(item_id=item_id, quantity=quantity))
        return tuple(returns)
