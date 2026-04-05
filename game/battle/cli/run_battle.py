from __future__ import annotations

from pathlib import Path

from game.battle.application.session import BattleSession
from game.battle.infrastructure.master_data_repository import MasterDataRepository


def run_sample_battle() -> int:
    repo = MasterDataRepository(Path("data/master"))
    skills = repo.load_skills()
    effects = repo.load_status_effects()
    player = repo.load_character("char.main.rion")
    enemy = repo.load_enemy("enemy.ch01.port_wraith")

    session = BattleSession.from_definitions([player], [enemy], skills, effects)
    session.bind_unit_skills({player.id: player.skill_ids, enemy.id: enemy.skill_ids})

    round_no = 1
    while not session.state.is_finished() and round_no <= 20:
        results = session.step_round()
        print(f"[Round {round_no}]")
        for turn in results:
            summary = turn.summary
            if summary is None:
                continue
            skill_text = f" skill={summary.skill_id}" if summary.skill_id else ""
            print(
                f"- actor={summary.actor_id} action={summary.action_type}{skill_text} "
                f"target={summary.target_id} damage={summary.damage} hp_after={summary.target_hp_after}"
            )
            for log in turn.logs:
                print(f"  * {log}")
        round_no += 1

    print(f"winner={session.state.winner()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_sample_battle())
