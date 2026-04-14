from __future__ import annotations

from pathlib import Path

from game.battle.application.command_selection import choose_player_command
from game.battle.application.session import BattleSession
from game.battle.domain.entities import Team
from game.battle.domain.services import execute_turn
from game.battle.infrastructure.master_data_repository import MasterDataRepository


def run_sample_battle() -> int:
    repo = MasterDataRepository(Path("data/master"))
    skills = repo.load_skills()
    effects = repo.load_status_effects()
    enemy_ai_profiles = repo.load_enemy_ai_profiles()
    enemy_ai_bindings = repo.load_enemy_ai_bindings()
    boss_encounters = repo.load_boss_encounters()
    player = repo.load_character("char.main.rion")
    encounter_id = "encounter.ch01.port_wraith"
    enemies, runtime_enemy_map = repo.build_enemy_party(encounter_id)

    session = BattleSession.create(
        [player],
        enemies,
        skills,
        effects,
        enemy_ai_profiles=enemy_ai_profiles,
        enemy_ai_by_enemy_id=enemy_ai_bindings,
        runtime_enemy_map=runtime_enemy_map,
        encounter_id=encounter_id,
        boss_encounters=boss_encounters,
    )
    session.bind_unit_skills({player.id: player.skill_ids, **{enemy.id: enemy.skill_ids for enemy in enemies}})

    round_no = 1
    while not session.state.is_finished() and round_no <= 20:
        results = []
        for actor_id in session.state.turn_order():
            def _command_factory(state, acting_unit):
                if acting_unit.team == Team.PLAYER:
                    return choose_player_command(
                        state=state,
                        actor=acting_unit,
                        skills=session.skills,
                        unit_skill_ids=session.unit_skill_ids(acting_unit.unit_id),
                    )
                return session.default_command_factory(state, acting_unit)

            turn = execute_turn(
                state=session.state,
                actor_id=actor_id,
                command_factory=_command_factory,
                skills=session.skills,
                effect_definitions=session.effect_definitions,
            )
            if turn.acted:
                results.append(turn)
            if turn.winner is not None:
                break

        print(f"[Round {round_no}]")
        enemy_lines = [
            f"{unit.unit_id}:hp={unit.hp}:alive={unit.alive}"
            for unit in sorted(
                (c for c in session.state.combatants.values() if c.team.value == "enemy"),
                key=lambda c: c.unit_id,
            )
        ]
        print(f"- enemies={' | '.join(enemy_lines)}")
        for turn in results:
            summary = turn.summary
            if summary is None:
                continue
            skill_text = f" skill={summary.skill_id}" if summary.skill_id else ""
            target_text = ",".join(
                f"{target.target_id}(damage={target.damage},hp={target.target_hp_after},alive={target.target_alive})"
                for target in summary.target_results
            )
            print(f"- actor={summary.actor_id} action={summary.action_type}{skill_text} targets=[{target_text}]")
            for log in turn.logs:
                print(f"  * {log}")
        round_no += 1

    print(f"winner={session.state.winner()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_sample_battle())
