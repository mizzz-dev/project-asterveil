from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from game.battle.domain.entities import SkillDefinition, Stats, StatusEffectDefinition, Team, UnitDefinition


@dataclass(frozen=True)
class EncounterEnemyDefinition:
    enemy_id: str
    count: int = 1
    slot: str | None = None


@dataclass(frozen=True)
class EncounterDefinition:
    encounter_id: str
    enemies: tuple[EncounterEnemyDefinition, ...]
    description: str = ""


class MasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_skills(self) -> dict[str, SkillDefinition]:
        skills_path = self._root / "skills.sample.json"
        raw = json.loads(skills_path.read_text(encoding="utf-8"))
        result: dict[str, SkillDefinition] = {}
        for item in raw:
            damage_block = next(block for block in item["effect_blocks"] if block["type"] == "damage")
            apply_effect_ids = tuple(
                str(block["effect_id"])
                for block in item["effect_blocks"]
                if block.get("type") == "apply_effect" and block.get("effect_id")
            )
            raw_target_count = item.get("target_count")
            target_count = int(raw_target_count) if raw_target_count is not None else None
            if target_count is not None and target_count <= 0:
                raise ValueError(f"skills.sample.json target_count must be >= 1 skill={item['id']}")

            result[item["id"]] = SkillDefinition(
                id=item["id"],
                target_type=item["target_type"],
                target_scope=str(item.get("target_scope", self._normalize_target_scope(item["target_type"]))),
                sp_cost=item["cost"]["sp"],
                power=float(damage_block["power"]),
                target_count=target_count,
                apply_effect_ids=apply_effect_ids,
            )
        return result

    def load_encounters(self) -> dict[str, EncounterDefinition]:
        encounters_path = self._root / "encounters.sample.json"
        raw = json.loads(encounters_path.read_text(encoding="utf-8"))
        encounters: dict[str, EncounterDefinition] = {}
        for item in raw:
            encounter_id = str(item.get("encounter_id") or item.get("id") or "")
            if not encounter_id:
                raise ValueError("encounters.sample.json missing field=encounter_id")

            enemy_entries: list[EncounterEnemyDefinition] = []
            if "enemies" in item:
                for entry in item.get("enemies", []):
                    enemy_id = str(entry.get("enemy_id") or "")
                    if not enemy_id:
                        raise ValueError(f"encounter enemy missing enemy_id encounter={encounter_id}")
                    enemy_entries.append(
                        EncounterEnemyDefinition(
                            enemy_id=enemy_id,
                            count=max(1, int(entry.get("count", 1))),
                            slot=str(entry["slot"]) if "slot" in entry else None,
                        )
                    )
            elif "enemy_id" in item:
                enemy_entries.append(EncounterEnemyDefinition(enemy_id=str(item["enemy_id"]), count=1))
            else:
                raise ValueError(f"encounters.sample.json missing enemies encounter={encounter_id}")

            encounters[encounter_id] = EncounterDefinition(
                encounter_id=encounter_id,
                enemies=tuple(enemy_entries),
                description=str(item.get("description", "")),
            )
        return encounters

    def build_enemy_party(self, encounter_id: str) -> tuple[list[UnitDefinition], dict[str, str]]:
        encounters = self.load_encounters()
        encounter = encounters.get(encounter_id)
        if encounter is None:
            raise ValueError(f"Unknown encounter_id: {encounter_id}")

        units: list[UnitDefinition] = []
        runtime_to_enemy_id: dict[str, str] = {}
        for entry in encounter.enemies:
            base_unit = self.load_enemy(entry.enemy_id)
            for index in range(1, entry.count + 1):
                runtime_id = f"{entry.enemy_id}#{index}"
                if runtime_id in runtime_to_enemy_id:
                    runtime_id = f"{entry.enemy_id}#{len(runtime_to_enemy_id) + 1}"
                instance = replace(base_unit, id=runtime_id)
                units.append(instance)
                runtime_to_enemy_id[runtime_id] = entry.enemy_id
        return units, runtime_to_enemy_id

    def load_status_effects(self) -> dict[str, StatusEffectDefinition]:
        effects_path = self._root / "status_effects.sample.json"
        raw = json.loads(effects_path.read_text(encoding="utf-8"))
        effects: dict[str, StatusEffectDefinition] = {}
        for item in raw:
            definition = StatusEffectDefinition(
                effect_id=str(item["effect_id"]),
                name=str(item["name"]),
                effect_type=str(item["effect_type"]),
                target_stat=str(item["target_stat"]),
                magnitude=float(item["magnitude"]),
                duration_turns=int(item["duration_turns"]),
                application_rule=str(item["application_rule"]),
                clear_on_rest=bool(item["clear_on_rest"]),
                removable_by_item=bool(item["removable_by_item"]),
                description=str(item.get("description", "")),
            )
            effects[definition.effect_id] = definition
        return effects

    def load_character(self, character_id: str) -> UnitDefinition:
        characters_path = self._root / "characters.sample.json"
        raw = json.loads(characters_path.read_text(encoding="utf-8"))
        item = next(c for c in raw if c["id"] == character_id)
        base = item["base_stats"]
        return UnitDefinition(
            id=item["id"],
            team=Team.PLAYER,
            stats=Stats(hp=base["hp"], atk=base["atk"], defense=base["def"], spd=base["spd"]),
            skill_ids=tuple(item.get("initial_skill_ids", [])),
        )

    def load_enemy(self, enemy_id: str) -> UnitDefinition:
        enemies_path = self._root / "enemies.sample.json"
        raw = json.loads(enemies_path.read_text(encoding="utf-8"))
        item = next(c for c in raw if c["id"] == enemy_id)
        base = item["stats"]
        return UnitDefinition(
            id=item["id"],
            team=Team.ENEMY,
            stats=Stats(hp=base["hp"], atk=base["atk"], defense=base["def"], spd=base["spd"]),
            skill_ids=tuple(item.get("skill_ids", [])),
        )

    def _normalize_target_scope(self, target_type: str) -> str:
        return "all_enemies" if target_type == "all" else "single_enemy"
