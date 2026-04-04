from __future__ import annotations

import json
from pathlib import Path

from game.battle.domain.entities import SkillDefinition, Stats, Team, UnitDefinition


class MasterDataRepository:
    def __init__(self, root: Path) -> None:
        self._root = root

    def load_skills(self) -> dict[str, SkillDefinition]:
        skills_path = self._root / "skills.sample.json"
        raw = json.loads(skills_path.read_text(encoding="utf-8"))
        result: dict[str, SkillDefinition] = {}
        for item in raw:
            damage_block = next(block for block in item["effect_blocks"] if block["type"] == "damage")
            result[item["id"]] = SkillDefinition(
                id=item["id"],
                target_type=item["target_type"],
                sp_cost=item["cost"]["sp"],
                power=float(damage_block["power"]),
            )
        return result

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
            skill_ids=tuple(),
        )
