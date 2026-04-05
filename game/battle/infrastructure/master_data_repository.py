from __future__ import annotations

import json
from pathlib import Path

from game.battle.domain.entities import SkillDefinition, Stats, StatusEffectDefinition, Team, UnitDefinition


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
            result[item["id"]] = SkillDefinition(
                id=item["id"],
                target_type=item["target_type"],
                sp_cost=item["cost"]["sp"],
                power=float(damage_block["power"]),
                apply_effect_ids=apply_effect_ids,
            )
        return result

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
