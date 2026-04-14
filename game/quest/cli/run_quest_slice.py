from __future__ import annotations

from pathlib import Path
from typing import Any

from game.battle.application.equipment_passive_service import EquipmentPassiveService
from game.battle.application.session import BattleSession
from game.battle.domain.entities import Team
from game.battle.infrastructure.master_data_repository import MasterDataRepository
from game.quest.application.session import QuestSliceSession
from game.quest.domain.entities import BattleResult
from game.quest.domain.services import QuestProgressService
from game.quest.infrastructure.master_data_repository import QuestMasterDataRepository
from game.save.domain.entities import PartyActiveEffectState


def build_battle_executor(root: Path):
    battle_repo = MasterDataRepository(root)
    skills = battle_repo.load_skills()
    effects = battle_repo.load_status_effects()
    enemy_ai_profiles = battle_repo.load_enemy_ai_profiles()
    enemy_ai_bindings = battle_repo.load_enemy_ai_bindings()
    boss_encounters = battle_repo.load_boss_encounters()
    equipment_passives = EquipmentPassiveService(battle_repo.load_equipment_passives())
    base_player = battle_repo.load_character("char.main.rion")

    def execute(encounter_id: str, party_members: list[Any] | None = None) -> BattleResult:
        player = base_player
        if party_members:
            member = party_members[0]
            player = base_player.__class__(
                id=str(getattr(member, "character_id")),
                team=base_player.team,
                stats=base_player.stats.__class__(
                    hp=int(getattr(member, "max_hp")),
                    atk=int(getattr(member, "atk")),
                    defense=int(getattr(member, "defense")),
                    spd=int(getattr(member, "spd")),
                ),
                skill_ids=tuple(getattr(member, "unlocked_skill_ids", base_player.skill_ids)),
            )
        enemies, runtime_to_enemy_id = battle_repo.build_enemy_party(encounter_id)
        member_equipped = dict(getattr(member, "equipped", {})) if party_members else {}
        session = BattleSession.create(
            [player],
            enemies,
            skills,
            effects,
            enemy_ai_profiles=enemy_ai_profiles,
            enemy_ai_by_enemy_id=enemy_ai_bindings,
            runtime_enemy_map=runtime_to_enemy_id,
            encounter_id=encounter_id,
            boss_encounters=boss_encounters,
            equipment_passive_service=equipment_passives,
            unit_equipment={player.id: member_equipped},
        )
        session.bind_unit_skills(
            {
                player.id: player.skill_ids,
                **{enemy.id: enemy.skill_ids for enemy in enemies},
            }
        )

        winner = session.run_until_finished()
        if party_members:
            actor_state = session.state.combatants[player.id]
            member = party_members[0]
            member.current_hp = actor_state.hp
            member.current_sp = actor_state.sp
            member.alive = actor_state.alive
            member.active_effects = [
                PartyActiveEffectState(effect_id=effect.effect_id, remaining_turns=effect.remaining_turns)
                for effect in actor_state.active_effects
            ]
        player_won = winner == Team.PLAYER
        defeated = tuple(
            runtime_to_enemy_id[combatant.unit_id]
            for combatant in session.state.combatants.values()
            if combatant.team == Team.ENEMY and not combatant.alive
        )
        return BattleResult(encounter_id=encounter_id, player_won=player_won, defeated_enemy_ids=defeated)

    return execute


def run_quest_vertical_slice() -> int:
    master_root = Path("data/master")
    quest_repo = QuestMasterDataRepository(master_root)

    quest_defs = quest_repo.load_quests()
    event_defs = quest_repo.load_events()

    session = QuestSliceSession(
        quest_service=QuestProgressService(quest_defs),
        events=event_defs,
        battle_executor=build_battle_executor(master_root),
    )

    print("[Event] 導入イベント")
    for log in session.play_event("event.ch01.port_request"):
        print(f"- {log}")

    quest_state = session.quest_states["quest.ch01.missing_port_record"]
    if quest_state.status.value == "ready_to_complete":
        print("[Event] 報告イベント")
        for log in session.play_event("event.ch01.port_report"):
            print(f"- {log}")

    print("[Summary]")
    for quest_id, state in session.quest_states.items():
        print(f"- {quest_id}: status={state.status.value}, progress={state.objective_progress}")
    print(f"- world_flags={sorted(session.world_flags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_quest_vertical_slice())
