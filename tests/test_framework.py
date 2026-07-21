import unittest

from backend.app.core.models import Move, PlayerProfile
from backend.app.core.store import InMemoryGameStore
from backend.app.games.monopoly.game import MonopolyGame


class FrameworkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.players = [
            PlayerProfile(id="p1", name="Human", is_human=True, skill_level=0.3),
            PlayerProfile(id="p2", name="AI", is_human=False, skill_level=0.8),
        ]

    def test_monopoly_start_sets_initial_state(self):
        game = MonopolyGame()
        state = game.start(self.players)
        self.assertEqual(state.game_type, "monopoly")
        self.assertEqual(state.current_player_id, "p1")
        self.assertEqual(state.board["positions"]["p1"], 0)

    def test_roll_move_updates_position_and_turn(self):
        game = MonopolyGame()
        game.start(self.players)
        state = game.apply_move(Move(player_id="p1", action="roll_dice", payload={"roll": 5}))
        self.assertEqual(state.board["positions"]["p1"], 5)
        self.assertEqual(state.current_player_id, "p2")

    def test_passing_go_awards_money(self):
        game = MonopolyGame()
        game.start(self.players)
        game.state.board["positions"]["p1"] = 39
        game.state.board["money"]["p1"] = 1500
        state = game.apply_move(Move(player_id="p1", action="roll_dice", payload={"roll": 2}))
        self.assertEqual(state.board["positions"]["p1"], 1)
        self.assertEqual(state.board["money"]["p1"], 1700)

    def test_store_can_retrieve_saved_game(self):
        game = MonopolyGame()
        state = game.start(self.players)
        store = InMemoryGameStore()
        store.save(game)
        loaded = store.get(state.game_id)
        self.assertEqual(loaded.state.game_id, state.game_id)


if __name__ == "__main__":
    unittest.main()
