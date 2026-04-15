from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


SAVE_VERSION = 1


@dataclass
class PlayerProfileState:
    difficulty: str = "standard"
    play_time_sec: int = 0
    last_saved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PartyActiveEffectState:
    effect_id: str
    remaining_turns: int


@dataclass
class PartyMemberState:
    character_id: str
    level: int
    current_exp: int = 0
    next_level_exp: int = 100
    max_hp: int = 1
    current_hp: int = 1
    max_sp: int = 0
    current_sp: int = 0
    atk: int = 1
    defense: int = 1
    spd: int = 1
    alive: bool = True
    equipped: dict[str, str] = field(default_factory=dict)
    unlocked_skill_ids: list[str] = field(default_factory=list)
    active_effects: list[PartyActiveEffectState] = field(default_factory=list)


@dataclass
class QuestSaveState:
    status: str
    objective_progress: list[int]
    objective_item_progress: list[dict[str, int]] = field(default_factory=list)
    reward_claimed: bool = False


@dataclass
class SaveData:
    save_version: int
    player_profile: PlayerProfileState
    party_members: list[PartyMemberState]
    quest_state: dict[str, QuestSaveState]
    world_flags: dict[str, Any]
    progression: dict[str, Any] = field(default_factory=dict)
    inventory_state: dict[str, Any] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "save_version": self.save_version,
            "player_profile": {
                "difficulty": self.player_profile.difficulty,
                "play_time_sec": self.player_profile.play_time_sec,
                "last_saved_at": self.player_profile.last_saved_at,
            },
            "party_state": {
                "members": [
                    {
                        "character_id": member.character_id,
                        "level": member.level,
                        "current_exp": member.current_exp,
                        "next_level_exp": member.next_level_exp,
                        "max_hp": member.max_hp,
                        "current_hp": member.current_hp,
                        "max_sp": member.max_sp,
                        "current_sp": member.current_sp,
                        "atk": member.atk,
                        "defense": member.defense,
                        "spd": member.spd,
                        "alive": member.alive,
                        "equipped": member.equipped,
                        "unlocked_skill_ids": member.unlocked_skill_ids,
                        "active_effects": [
                            {
                                "effect_id": effect.effect_id,
                                "remaining_turns": effect.remaining_turns,
                            }
                            for effect in member.active_effects
                        ],
                    }
                    for member in self.party_members
                ]
            },
            "quest_state": {
                quest_id: {
                    "status": state.status,
                    "objective_progress": state.objective_progress,
                    "objective_item_progress": state.objective_item_progress,
                    "reward_claimed": state.reward_claimed,
                }
                for quest_id, state in self.quest_state.items()
            },
            "world_flags": self.world_flags,
            "progression": self.progression,
            "inventory_state": self.inventory_state,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "SaveData":
        required_top_level = ["save_version", "player_profile", "party_state", "quest_state", "world_flags"]
        for field_name in required_top_level:
            if field_name not in raw:
                raise ValueError(f"save_data missing field={field_name}")

        if int(raw["save_version"]) != SAVE_VERSION:
            raise ValueError(f"unsupported save_version={raw['save_version']}")

        player_profile_raw = raw["player_profile"]
        for field_name in ["difficulty", "play_time_sec", "last_saved_at"]:
            if field_name not in player_profile_raw:
                raise ValueError(f"player_profile missing field={field_name}")

        party_raw = raw["party_state"]
        if "members" not in party_raw:
            raise ValueError("party_state missing field=members")

        party_members = []
        for member in party_raw["members"]:
            for field_name in ["character_id", "level", "current_hp", "current_sp", "alive"]:
                if field_name not in member:
                    raise ValueError(f"party_member missing field={field_name}")
            max_hp = int(member.get("max_hp", member["current_hp"]))
            max_sp = int(member.get("max_sp", member["current_sp"]))
            party_members.append(
                PartyMemberState(
                    character_id=str(member["character_id"]),
                    level=int(member["level"]),
                    current_exp=int(member.get("current_exp", 0)),
                    next_level_exp=int(member.get("next_level_exp", 100)),
                    max_hp=max_hp,
                    current_hp=int(member["current_hp"]),
                    max_sp=max_sp,
                    current_sp=int(member["current_sp"]),
                    atk=int(member.get("atk", 1)),
                    defense=int(member.get("defense", 1)),
                    spd=int(member.get("spd", 1)),
                    alive=bool(member["alive"]),
                    equipped=dict(member.get("equipped", {})),
                    unlocked_skill_ids=[str(skill_id) for skill_id in member.get("unlocked_skill_ids", [])],
                    active_effects=[
                        PartyActiveEffectState(
                            effect_id=str(effect.get("effect_id")),
                            remaining_turns=int(effect.get("remaining_turns", 0)),
                        )
                        for effect in member.get("active_effects", [])
                        if effect.get("effect_id")
                    ],
                )
            )

        quests: dict[str, QuestSaveState] = {}
        for quest_id, quest_raw in raw["quest_state"].items():
            if "status" not in quest_raw or "objective_progress" not in quest_raw:
                raise ValueError(f"quest_state missing status/objective_progress quest_id={quest_id}")
            objective_progress = quest_raw["objective_progress"]
            if not isinstance(objective_progress, list):
                raise ValueError(f"objective_progress must be list quest_id={quest_id}")
            quests[quest_id] = QuestSaveState(
                status=str(quest_raw["status"]),
                objective_progress=[int(value) for value in objective_progress],
                objective_item_progress=[
                    {str(item_id): int(amount) for item_id, amount in per_objective.items()}
                    for per_objective in quest_raw.get("objective_item_progress", [])
                ],
                reward_claimed=bool(quest_raw.get("reward_claimed", False)),
            )

        profile = PlayerProfileState(
            difficulty=str(player_profile_raw["difficulty"]),
            play_time_sec=int(player_profile_raw["play_time_sec"]),
            last_saved_at=str(player_profile_raw["last_saved_at"]),
        )

        return cls(
            save_version=SAVE_VERSION,
            player_profile=profile,
            party_members=party_members,
            quest_state=quests,
            world_flags=dict(raw["world_flags"]),
            progression=dict(raw.get("progression", {})),
            inventory_state=dict(raw.get("inventory_state", {})),
            meta=dict(raw.get("meta", {})),
        )
