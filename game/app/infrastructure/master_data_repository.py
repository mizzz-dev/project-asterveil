from __future__ import annotations

import json
from pathlib import Path

from game.app.application.equipment_service import EquipmentDefinition
from game.app.application.inn_service import InnDefinition
from game.app.application.reward_services import BattleReward, RewardBundle, RewardItem


class AppMasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_items(self) -> dict[str, dict]:
        raw = json.loads((self._root / "items.sample.json").read_text(encoding="utf-8"))
        items: dict[str, dict] = {}
        for item in raw:
            item_id = str(item.get("item_id") or item.get("id") or "")
            if not item_id:
                raise ValueError("items.sample.json missing field=item_id")
            for field in ["category", "name"]:
                if field not in item:
                    raise ValueError(f"items.sample.json missing field={field} item={item_id}")

            normalized = dict(item)
            normalized["id"] = item_id
            normalized["item_id"] = item_id
            items[item_id] = normalized
        return items

    def load_equipment(self) -> dict[str, EquipmentDefinition]:
        raw = json.loads((self._root / "equipment.sample.json").read_text(encoding="utf-8"))
        equipment: dict[str, EquipmentDefinition] = {}
        for entry in raw:
            equipment_id = str(entry.get("equipment_id") or entry.get("id") or "")
            if not equipment_id:
                raise ValueError("equipment.sample.json missing field=equipment_id")
            slot_type = str(entry.get("slot_type") or entry.get("slot") or "")
            if not slot_type:
                raise ValueError(f"equipment.sample.json missing field=slot_type equipment_id={equipment_id}")
            stat_modifiers = dict(entry.get("stat_modifiers") or {})
            equipment[equipment_id] = EquipmentDefinition(
                equipment_id=equipment_id,
                name=str(entry.get("name") or equipment_id),
                slot_type=slot_type,
                stat_modifiers={str(k): int(v) for k, v in stat_modifiers.items()},
                description=str(entry.get("description", "")),
                price=int(entry.get("price", 0)),
                stackable=bool(entry.get("stackable", False)),
            )
        return equipment

    def load_battle_rewards(self, valid_item_ids: set[str]) -> dict[str, BattleReward]:
        raw = json.loads((self._root / "reward_tables.sample.json").read_text(encoding="utf-8"))
        rewards: dict[str, BattleReward] = {}
        for reward in raw.get("battle_rewards", []):
            encounter_id = reward.get("encounter_id")
            if not encounter_id:
                raise ValueError("reward_tables.sample.json battle_rewards missing encounter_id")
            item_rewards = tuple(
                self._validate_reward_item(item, valid_item_ids, source=f"encounter={encounter_id}")
                for item in reward.get("items", [])
            )
            rewards[encounter_id] = BattleReward(
                encounter_id=encounter_id,
                rewards_on_win=RewardBundle(
                    exp=int(reward.get("exp", 0)),
                    gold=int(reward.get("gold", 0)),
                    items=item_rewards,
                ),
            )
        return rewards

    def load_inns(self) -> dict[str, InnDefinition]:
        raw = json.loads((self._root / "inns.sample.json").read_text(encoding="utf-8"))
        inns: dict[str, InnDefinition] = {}
        for entry in raw:
            inn_id = str(entry.get("inn_id") or "")
            if not inn_id:
                raise ValueError("inns.sample.json missing field=inn_id")
            stay_price = int(entry.get("stay_price", 0))
            if stay_price < 0:
                raise ValueError(f"inns.sample.json stay_price must be >= 0 inn_id={inn_id}")
            inns[inn_id] = InnDefinition(
                inn_id=inn_id,
                name=str(entry.get("name") or inn_id),
                stay_price=stay_price,
                description=str(entry.get("description", "")),
                revive_knocked_out_members=bool(entry.get("revive_knocked_out_members", True)),
                location_id=str(entry.get("location_id", "")),
            )
        return inns

    def _validate_reward_item(self, item: dict, valid_item_ids: set[str], source: str) -> RewardItem:
        for field in ["item_id", "amount"]:
            if field not in item:
                raise ValueError(f"reward item missing field={field}: {source}")
        item_id = str(item["item_id"])
        if item_id not in valid_item_ids:
            raise ValueError(f"unknown item_id in rewards: {item_id} ({source})")
        amount = int(item["amount"])
        if amount <= 0:
            raise ValueError(f"item amount must be > 0: {amount} ({source})")
        return RewardItem(item_id=item_id, amount=amount)
