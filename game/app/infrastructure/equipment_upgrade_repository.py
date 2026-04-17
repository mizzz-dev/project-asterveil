from __future__ import annotations

import json
from pathlib import Path

from game.app.application.equipment_upgrade_service import (
    EquipmentUpgradeDefinition,
    EquipmentUpgradeLevelDefinition,
    UpgradeRequiredItem,
)


class EquipmentUpgradeMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load(self, *, valid_equipment_ids: set[str], valid_item_ids: set[str]) -> dict[str, EquipmentUpgradeDefinition]:
        path = self._root / "equipment_upgrades.sample.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        definitions: dict[str, EquipmentUpgradeDefinition] = {}
        for row in raw:
            equipment_id = str(row.get("equipment_id") or "")
            if not equipment_id:
                raise ValueError("equipment_upgrades.sample.json missing field=equipment_id")
            if equipment_id not in valid_equipment_ids:
                raise ValueError(f"equipment_upgrades.sample.json unknown equipment_id={equipment_id}")
            upgrade_levels_raw = row.get("upgrade_levels", [])
            levels: list[EquipmentUpgradeLevelDefinition] = []
            seen_levels: set[int] = set()
            for level_row in upgrade_levels_raw:
                level = int(level_row.get("upgrade_level", 0))
                if level <= 0:
                    raise ValueError(
                        f"equipment_upgrades.sample.json upgrade_level must be >=1 equipment_id={equipment_id}"
                    )
                if level in seen_levels:
                    raise ValueError(
                        f"equipment_upgrades.sample.json duplicate upgrade_level equipment_id={equipment_id} level={level}"
                    )
                seen_levels.add(level)
                required_items: list[UpgradeRequiredItem] = []
                for item in level_row.get("required_items", []):
                    item_id = str(item.get("item_id") or "")
                    quantity = int(item.get("quantity", 0))
                    if item_id not in valid_item_ids:
                        raise ValueError(
                            f"equipment_upgrades.sample.json unknown required item_id={item_id} equipment_id={equipment_id}"
                        )
                    if quantity <= 0:
                        raise ValueError(
                            f"equipment_upgrades.sample.json quantity must be >0 equipment_id={equipment_id} item_id={item_id}"
                        )
                    required_items.append(UpgradeRequiredItem(item_id=item_id, quantity=quantity))
                levels.append(
                    EquipmentUpgradeLevelDefinition(
                        upgrade_level=level,
                        required_workshop_level=max(1, int(level_row.get("required_workshop_level", 1))),
                        required_items=tuple(required_items),
                        stat_bonus={str(k): int(v) for k, v in dict(level_row.get("stat_bonus") or {}).items()},
                        passive_modifiers=tuple(dict(entry) for entry in level_row.get("passive_modifiers", [])),
                        description=str(level_row.get("description", "")),
                    )
                )
            levels.sort(key=lambda entry: entry.upgrade_level)
            definitions[equipment_id] = EquipmentUpgradeDefinition(
                equipment_id=equipment_id,
                upgrade_enabled=bool(row.get("upgrade_enabled", False)),
                upgrade_levels=tuple(levels),
            )
        return definitions
