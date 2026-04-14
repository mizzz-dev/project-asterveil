from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from game.battle.application.boss_phase import (
    BossEncounterDefinition,
    BossPhaseDefinition,
    BossPhaseEvent,
    parse_boss_phase_condition,
)
from game.battle.application.enemy_ai import EnemyAiProfile, EnemyAiRule
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
            effect_blocks = item.get("effect_blocks", [])
            damage_block = next((block for block in effect_blocks if block["type"] == "damage"), None)
            heal_block = next((block for block in effect_blocks if block["type"] == "heal"), None)
            cure_block = next((block for block in effect_blocks if block["type"] == "cure_effect"), None)
            apply_effect_ids = tuple(
                str(block["effect_id"])
                for block in effect_blocks
                if block.get("type") == "apply_effect" and block.get("effect_id")
            )
            remove_effect_ids: tuple[str, ...] = tuple()
            if cure_block is not None:
                remove_effect_ids = tuple(str(effect_id) for effect_id in cure_block.get("effect_ids", []))
                if not remove_effect_ids and cure_block.get("effect_id"):
                    remove_effect_ids = (str(cure_block["effect_id"]),)
            raw_target_count = item.get("target_count")
            target_count = int(raw_target_count) if raw_target_count is not None else None
            if target_count is not None and target_count <= 0:
                raise ValueError(f"skills.sample.json target_count must be >= 1 skill={item['id']}")

            effect_kind = str(item.get("effect_kind", "")).strip()
            if not effect_kind:
                if heal_block is not None:
                    effect_kind = "heal"
                elif remove_effect_ids:
                    effect_kind = "cure_effect"
                elif apply_effect_ids and damage_block is None:
                    effect_kind = "apply_effect"
                else:
                    effect_kind = "damage"

            if effect_kind == "damage" and damage_block is None:
                raise ValueError(f"skills.sample.json damage skill missing damage block skill={item['id']}")
            if effect_kind == "heal" and heal_block is None and item.get("heal_power") is None:
                raise ValueError(f"skills.sample.json heal skill missing heal_power skill={item['id']}")

            result[item["id"]] = SkillDefinition(
                id=item["id"],
                target_type=item["target_type"],
                target_scope=str(item.get("target_scope", self._normalize_target_scope(item["target_type"]))),
                effect_kind=effect_kind,
                sp_cost=item["cost"]["sp"],
                power=float(damage_block["power"]) if damage_block is not None else 0.0,
                heal_power=float(item.get("heal_power", heal_block.get("power") if heal_block else 0.0)),
                target_count=target_count,
                apply_effect_ids=apply_effect_ids,
                remove_effect_ids=remove_effect_ids,
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

    def load_boss_encounters(self) -> dict[str, BossEncounterDefinition]:
        path = self._root / "boss_encounters.sample.json"
        if not path.exists():
            return {}
        raw = json.loads(path.read_text(encoding="utf-8"))
        result: dict[str, BossEncounterDefinition] = {}
        for item in raw:
            encounter_id = str(item.get("encounter_id") or "")
            boss_enemy_id = str(item.get("boss_enemy_id") or "")
            if not encounter_id or not boss_enemy_id:
                raise ValueError("boss_encounters.sample.json missing encounter_id or boss_enemy_id")
            phases: list[BossPhaseDefinition] = []
            for phase in item.get("phases", []):
                phase_id = str(phase.get("phase_id") or "")
                if not phase_id:
                    raise ValueError(f"boss_encounters.sample.json missing phase_id encounter={encounter_id}")
                events = tuple(
                    BossPhaseEvent(
                        event_type=str(event.get("event_type", "")),
                        message=str(event["message"]) if event.get("message") else None,
                        effect_id=str(event["effect_id"]) if event.get("effect_id") else None,
                        flag_id=str(event["flag_id"]) if event.get("flag_id") else None,
                    )
                    for event in phase.get("on_enter_events", [])
                )
                phases.append(
                    BossPhaseDefinition(
                        phase_id=phase_id,
                        display_name=str(phase.get("display_name") or phase_id),
                        ai_profile_id=str(phase["ai_profile_id"]) if phase.get("ai_profile_id") else None,
                        enter_condition=parse_boss_phase_condition(phase.get("enter_condition")),
                        on_enter_events=events,
                    )
                )
            if not phases:
                raise ValueError(f"boss_encounters.sample.json requires phases encounter={encounter_id}")
            result[encounter_id] = BossEncounterDefinition(
                encounter_id=encounter_id,
                boss_enemy_id=boss_enemy_id,
                phases=tuple(phases),
            )
        return result

    def load_enemy_ai_profiles(self) -> dict[str, EnemyAiProfile]:
        ai_path = self._root / "enemy_ai.sample.json"
        raw = json.loads(ai_path.read_text(encoding="utf-8"))
        profiles: dict[str, EnemyAiProfile] = {}
        for item in raw:
            profile_id = str(item["ai_profile_id"])
            rules = tuple(
                EnemyAiRule(
                    rule_id=str(rule["rule_id"]),
                    priority=int(rule["priority"]),
                    action_type=str(rule["action_type"]),
                    skill_id=str(rule["skill_id"]) if rule.get("skill_id") else None,
                    conditions=tuple(dict(condition) for condition in rule.get("conditions", [])),
                    target_rule=str(rule.get("target_rule", "random_enemy")),
                )
                for rule in item.get("action_rules", [])
            )
            profiles[profile_id] = EnemyAiProfile(ai_profile_id=profile_id, action_rules=rules)
        return profiles

    def load_enemy_ai_bindings(self) -> dict[str, str]:
        enemies_path = self._root / "enemies.sample.json"
        raw = json.loads(enemies_path.read_text(encoding="utf-8"))
        return {
            str(item["id"]): str(item["ai_profile_id"])
            for item in raw
            if str(item.get("ai_profile_id", "")).strip()
        }

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
