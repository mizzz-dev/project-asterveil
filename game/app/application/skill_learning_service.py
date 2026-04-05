from __future__ import annotations

from dataclasses import dataclass

from game.save.domain.entities import PartyMemberState


@dataclass(frozen=True)
class LearnableSkill:
    skill_id: str
    required_level: int
    learn_type: str = "auto"
    description: str = ""


class SkillLearningService:
    def __init__(
        self,
        learnable_by_character: dict[str, tuple[LearnableSkill, ...]],
        initial_skill_ids_by_character: dict[str, tuple[str, ...]],
    ) -> None:
        self._learnable_by_character = learnable_by_character
        self._initial_skill_ids_by_character = initial_skill_ids_by_character

    def initial_skill_ids_for_character(self, character_id: str) -> tuple[str, ...]:
        return self._initial_skill_ids_by_character.get(character_id, tuple())

    def apply_initial_skills(self, member: PartyMemberState) -> list[str]:
        return self._learn_missing_skills(member, self.initial_skill_ids_for_character(member.character_id), reason="initial")

    def apply_level_up_skills(self, member: PartyMemberState, previous_level: int) -> list[str]:
        learnable = self._learnable_by_character.get(member.character_id, tuple())
        candidate_ids = [
            entry.skill_id
            for entry in learnable
            if entry.learn_type == "auto" and previous_level < entry.required_level <= member.level
        ]
        return self._learn_missing_skills(member, candidate_ids, reason="level_up")

    def _learn_missing_skills(self, member: PartyMemberState, candidate_ids: list[str] | tuple[str, ...], reason: str) -> list[str]:
        logs: list[str] = []
        learned = set(member.unlocked_skill_ids)
        for skill_id in candidate_ids:
            if skill_id in learned:
                continue
            member.unlocked_skill_ids.append(skill_id)
            learned.add(skill_id)
            logs.append(f"learned_skill:{member.character_id}:{skill_id}:reason={reason}:level={member.level}")
        return logs
