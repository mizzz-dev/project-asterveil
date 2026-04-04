from __future__ import annotations

from dataclasses import dataclass

from game.quest.domain.entities import QuestReward
from game.save.domain.entities import PartyMemberState


@dataclass(frozen=True)
class RewardItem:
    item_id: str
    amount: int


@dataclass(frozen=True)
class RewardBundle:
    exp: int = 0
    gold: int = 0
    items: tuple[RewardItem, ...] = tuple()


@dataclass(frozen=True)
class BattleReward:
    encounter_id: str
    rewards_on_win: RewardBundle


class ProgressionService:
    def required_exp_for_level(self, level: int) -> int:
        if level < 1:
            raise ValueError(f"level must be >= 1: {level}")
        return 100 + (level - 1) * 50

    def grant_exp(self, member: PartyMemberState, exp: int) -> int:
        if exp < 0:
            raise ValueError(f"exp must be >= 0: {exp}")
        member.current_exp += exp
        level_ups = 0
        while member.current_exp >= member.next_level_exp:
            member.current_exp -= member.next_level_exp
            member.level += 1
            member.next_level_exp = self.required_exp_for_level(member.level)
            member.max_hp += 12
            member.max_sp += 4
            member.atk += 2
            member.defense += 1
            member.spd += 1
            member.current_hp = member.max_hp
            member.current_sp = member.max_sp
            level_ups += 1
        return level_ups


class RewardApplicationService:
    def __init__(self, progression: ProgressionService | None = None) -> None:
        self._progression = progression or ProgressionService()

    def apply(self, reward: RewardBundle, party_members: list[PartyMemberState], inventory_state: dict) -> list[str]:
        logs: list[str] = []
        if reward.exp > 0:
            for member in party_members:
                level_ups = self._progression.grant_exp(member, reward.exp)
                logs.append(
                    f"exp_applied:{member.character_id}:exp={reward.exp}:level={member.level}:level_ups={level_ups}"
                )
        if reward.gold > 0:
            inventory_state["gold"] = int(inventory_state.get("gold", 0)) + reward.gold
            logs.append(f"gold_applied:{reward.gold}:total={inventory_state['gold']}")
        if reward.items:
            items = inventory_state.setdefault("items", {})
            for item in reward.items:
                items[item.item_id] = int(items.get(item.item_id, 0)) + item.amount
                logs.append(f"item_applied:{item.item_id}:amount={item.amount}:total={items[item.item_id]}")
        return logs

    def from_quest_reward(self, reward: QuestReward) -> RewardBundle:
        return RewardBundle(
            exp=reward.exp,
            gold=reward.gold,
            items=tuple(RewardItem(item_id=item_id, amount=amount) for item_id, amount in reward.items),
        )
