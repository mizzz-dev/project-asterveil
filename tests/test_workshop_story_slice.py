from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import json

from game.app.application.playable_slice import PlayableSliceApplication
from game.app.application.workshop_story_service import WorkshopStoryService, WorkshopStoryState
from game.app.infrastructure.workshop_story_repository import WorkshopStoryMasterDataRepository


class WorkshopStorySliceTests(unittest.TestCase):
    def test_workshop_story_master_data_loading(self) -> None:
        repository = WorkshopStoryMasterDataRepository(Path("data/master"))
        quest_ids = {
            row["quest_id"]
            for row in json.loads((Path("data/master") / "quests.sample.json").read_text(encoding="utf-8"))
        }
        recipe_ids = {
            row["recipe_id"]
            for row in json.loads((Path("data/master") / "crafting_recipes.sample.json").read_text(encoding="utf-8"))
        }
        stages = repository.load(
            valid_npc_ids={
                "npc.astel.elder",
                "npc.astel.guard",
                "npc.astel.workshop_master",
                "npc.astel.workshop_apprentice",
            },
            valid_quest_ids=quest_ids,
            valid_recipe_ids=recipe_ids,
            valid_location_ids={"location.town.astel", "location.field.tidal_flats"},
            valid_field_event_ids={
                "event.field.tidal_flats.drift_supply",
                "event.field.tidal_flats.toxic_mushroom",
                "event.field.tidal_flats.sunken_shrine_switch",
            },
        )
        self.assertGreaterEqual(len(stages), 4)
        rank3_stage = next(stage for stage in stages if stage.storyline_id == "workshop.story.yeld.rank3_order_unlock")
        self.assertIn("quest.ch01.workshop_rank3_expedition", rank3_stage.unlock_rewards.quest_ids)

    def test_story_service_avoids_duplicate_unlock(self) -> None:
        repository = WorkshopStoryMasterDataRepository(Path("data/master"))
        stages = repository.load(
            valid_npc_ids={"npc.astel.workshop_master", "npc.astel.workshop_apprentice"},
            valid_quest_ids={"quest.ch01.workshop_rank3_expedition"},
            valid_recipe_ids={"recipe.craft.workshop_oceanic_polish"},
            valid_location_ids=set(),
            valid_field_event_ids=set(),
        )
        stage = next(stage for stage in stages if stage.storyline_id == "workshop.story.yeld.rank3_order_unlock")
        service = WorkshopStoryService()
        state = WorkshopStoryState()
        world_flags = {"flag.workshop.rank.2"}
        first_logs = service.apply_stage(stage=stage, state=state, world_flags=world_flags)
        second_logs = service.apply_stage(stage=stage, state=state, world_flags=world_flags)
        self.assertTrue(any(line.startswith("new_workshop_order_unlocked:") for line in first_logs))
        self.assertEqual(second_logs, ["workshop_story_unlock_skipped:already_seen:workshop.story.yeld.rank3_order_unlock"])

    def test_playable_workshop_story_rank3_unlock_and_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=lambda *_: None,
            )
            app.new_game()
            app.workshop_progress_state.level = 2
            app.quest_session.world_flags.add("flag.workshop.rank.2")

            first_talk = app.talk_to_npc("npc.astel.workshop_master")
            self.assertTrue(any("workshop_story_advanced:workshop.story.yeld.rank3_order_unlock" in line for line in first_talk))
            self.assertIn("flag.workshop.story.rank3.order_unlocked", app.quest_session.world_flags)

            app.workshop_progress_state.level = 3
            app.quest_session.world_flags.add("flag.workshop.rank.3")
            app.inventory_state["items"]["item.material.relic.deepsea_thread"] = 1
            accept_logs = app.accept_quest("quest.ch01.workshop_rank3_expedition")
            self.assertEqual(accept_logs, ["quest_accepted:quest.ch01.workshop_rank3_expedition"])
            turn_in_logs = app.turn_in_quest_items("quest.ch01.workshop_rank3_expedition", auto_complete=True)
            self.assertTrue(any(line.startswith("turn_in_success:quest.ch01.workshop_rank3_expedition") for line in turn_in_logs))
            self.assertIn("flag.workshop.story.rank3.order_completed", app.quest_session.world_flags)

            apprentice_logs = app.talk_to_npc("npc.astel.workshop_apprentice")
            self.assertTrue(any("workshop.story.luca.rank3_recipe_unlock" in line for line in apprentice_logs))
            self.assertIn("recipe.craft.workshop_oceanic_polish", app.unlocked_recipe_ids)

            app.perform_action("save")
            resumed = PlayableSliceApplication(
                master_root=Path("data/master"),
                save_file_path=Path(tmp_dir) / "slot_01.json",
                battle_executor=lambda *_: None,
            )
            ok, _ = resumed.continue_game()
            self.assertTrue(ok)
            self.assertIn("workshop.story.yeld.rank3_order_unlock", resumed.workshop_story_state.seen_stage_ids)
            self.assertIn("recipe.craft.workshop_oceanic_polish", resumed.workshop_story_state.unlocked_recipe_ids)
            self.assertIn("recipe.craft.workshop_oceanic_polish", resumed.unlocked_recipe_ids)


if __name__ == "__main__":
    unittest.main()
