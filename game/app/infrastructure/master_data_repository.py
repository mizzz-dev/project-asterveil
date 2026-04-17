from __future__ import annotations

import json
from pathlib import Path

from game.app.application.equipment_service import EquipmentDefinition, EquipmentPassiveDefinition
from game.app.application.equipment_set_service import (
    SUPPORTED_SET_BONUS_TYPES,
    EquipmentSetBonusDefinition,
    EquipmentSetDefinition,
)
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

    def load_status_effects(self) -> dict[str, dict]:
        raw = json.loads((self._root / "status_effects.sample.json").read_text(encoding="utf-8"))
        result: dict[str, dict] = {}
        for entry in raw:
            effect_id = str(entry.get("effect_id", ""))
            if not effect_id:
                raise ValueError("status_effects.sample.json missing field=effect_id")
            result[effect_id] = dict(entry)
        return result

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
            passive_effects = tuple(
                EquipmentPassiveDefinition(
                    passive_id=str(passive.get("passive_id") or ""),
                    passive_type=str(passive.get("passive_type") or ""),
                    target=str(passive.get("target", "self")),
                    parameters=dict(passive.get("parameters", {})),
                    description=str(passive.get("description", "")),
                )
                for passive in entry.get("passive_effects", [])
            )
            if any(not passive.passive_id or not passive.passive_type for passive in passive_effects):
                raise ValueError(f"equipment.sample.json passive requires passive_id/passive_type equipment_id={equipment_id}")

            equipment[equipment_id] = EquipmentDefinition(
                equipment_id=equipment_id,
                name=str(entry.get("name") or equipment_id),
                slot_type=slot_type,
                stat_modifiers={str(k): int(v) for k, v in stat_modifiers.items()},
                description=str(entry.get("description", "")),
                price=int(entry.get("price", 0)),
                stackable=bool(entry.get("stackable", False)),
                passive_effects=passive_effects,
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

    def load_initial_skill_ids_by_character(self) -> dict[str, tuple[str, ...]]:
        raw = json.loads((self._root / "characters.sample.json").read_text(encoding="utf-8"))
        result: dict[str, tuple[str, ...]] = {}
        for entry in raw:
            character_id = str(entry.get("id") or "")
            if not character_id:
                raise ValueError("characters.sample.json missing field=id")
            initial_skill_ids = tuple(str(skill_id) for skill_id in entry.get("initial_skill_ids", []))
            result[character_id] = initial_skill_ids
        return result

    def load_skill_learns(self) -> dict[str, tuple[dict, ...]]:
        raw = json.loads((self._root / "skill_learns.sample.json").read_text(encoding="utf-8"))
        result: dict[str, tuple[dict, ...]] = {}
        for entry in raw:
            character_id = str(entry.get("character_id") or "")
            if not character_id:
                raise ValueError("skill_learns.sample.json missing field=character_id")
            learnable = []
            for learn in entry.get("learnable_skills", []):
                skill_id = str(learn.get("skill_id") or "")
                if not skill_id:
                    raise ValueError(f"skill_learns.sample.json missing skill_id character_id={character_id}")
                required_level = int(learn.get("required_level", 0))
                if required_level <= 0:
                    raise ValueError(
                        f"skill_learns.sample.json required_level must be >= 1 character_id={character_id} skill_id={skill_id}"
                    )
                learnable.append(
                    {
                        "skill_id": skill_id,
                        "required_level": required_level,
                        "learn_type": str(learn.get("learn_type", "auto")),
                        "description": str(learn.get("description", "")),
                    }
                )
            result[character_id] = tuple(learnable)
        return result


    def load_equipment_sets(self, valid_equipment_ids: set[str]) -> dict[str, EquipmentSetDefinition]:
        path = self._root / "equipment_sets.sample.json"
        if not path.exists():
            return {}
        raw = json.loads(path.read_text(encoding="utf-8"))
        equipment_sets: dict[str, EquipmentSetDefinition] = {}
        for entry in raw:
            set_id = str(entry.get("set_id") or "")
            if not set_id:
                raise ValueError("equipment_sets.sample.json missing field=set_id")
            member_equipment_ids = tuple(str(equipment_id) for equipment_id in entry.get("member_equipment_ids", []))
            if not member_equipment_ids:
                raise ValueError(f"equipment_sets.sample.json missing member_equipment_ids set_id={set_id}")
            unknown_members = sorted(equipment_id for equipment_id in member_equipment_ids if equipment_id not in valid_equipment_ids)
            if unknown_members:
                raise ValueError(f"equipment_sets.sample.json unknown member_equipment_ids set_id={set_id}: {unknown_members}")

            bonuses: list[EquipmentSetBonusDefinition] = []
            for bonus in entry.get("set_bonuses", []):
                required_piece_count = int(bonus.get("required_piece_count", 0))
                bonus_type = str(bonus.get("bonus_type") or "")
                parameters = dict(bonus.get("parameters") or {})
                if required_piece_count <= 0:
                    raise ValueError(
                        f"equipment_sets.sample.json required_piece_count must be >=1 set_id={set_id}"
                    )
                if required_piece_count > len(member_equipment_ids):
                    raise ValueError(
                        f"equipment_sets.sample.json required_piece_count exceeds member count set_id={set_id}"
                    )
                if bonus_type not in SUPPORTED_SET_BONUS_TYPES:
                    raise ValueError(
                        f"equipment_sets.sample.json unsupported bonus_type={bonus_type} set_id={set_id}"
                    )
                if bonus_type == "stat_bonus" and not parameters:
                    raise ValueError(f"equipment_sets.sample.json stat_bonus requires parameters set_id={set_id}")
                if bonus_type in {"passive_effect", "status_resistance"}:
                    passive_id = str(parameters.get("passive_id") or "")
                    if not passive_id:
                        raise ValueError(
                            f"equipment_sets.sample.json passive bonus requires parameters.passive_id set_id={set_id}"
                        )
                bonuses.append(
                    EquipmentSetBonusDefinition(
                        required_piece_count=required_piece_count,
                        bonus_type=bonus_type,
                        parameters=parameters,
                        bonus_description=str(bonus.get("bonus_description", "")),
                    )
                )

            if not bonuses:
                raise ValueError(f"equipment_sets.sample.json missing set_bonuses set_id={set_id}")

            equipment_sets[set_id] = EquipmentSetDefinition(
                set_id=set_id,
                name=str(entry.get("name") or set_id),
                description=str(entry.get("description") or ""),
                member_equipment_ids=member_equipment_ids,
                set_bonuses=tuple(sorted(bonuses, key=lambda item: item.required_piece_count)),
            )
        return equipment_sets

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
