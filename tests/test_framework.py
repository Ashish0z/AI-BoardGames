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
        self.assertEqual(len(state.board["tiles"]), 40)

    def test_roll_into_property_requires_buy_or_skip(self):
        game = MonopolyGame()
        game.start(self.players)
        state = game.apply_move(Move(player_id="p1", action="roll_dice", payload={"die1": 1, "die2": 2}))
        pending = state.board["pending_action"]
        self.assertIsNotNone(pending)
        self.assertEqual(pending["type"], "buy_or_skip")
        self.assertEqual(state.current_player_id, "p1")

    def test_buy_property_claims_ownership(self):
        game = MonopolyGame()
        game.start(self.players)
        game.apply_move(Move(player_id="p1", action="roll_dice", payload={"die1": 1, "die2": 2}))
        state = game.apply_move(Move(player_id="p1", action="buy_property"))
        self.assertEqual(state.board["ownership"]["3"], "p1")
        self.assertIn(3, state.board["properties_by_player"]["p1"])

    def test_rent_is_paid_to_owner(self):
        game = MonopolyGame()
        game.start(self.players)
        game.state.board["ownership"]["3"] = "p1"
        game.state.board["properties_by_player"]["p1"].append(3)

        game.apply_move(Move(player_id="p1", action="end_turn"))
        state = game.apply_move(Move(player_id="p2", action="roll_dice", payload={"die1": 1, "die2": 2}))
        self.assertEqual(state.board["money"]["p2"], 1496)
        self.assertEqual(state.board["money"]["p1"], 1504)

    def test_passing_go_awards_money(self):
        game = MonopolyGame()
        game.start(self.players)
        game.state.board["positions"]["p1"] = 39
        game.state.board["money"]["p1"] = 1500
        state = game.apply_move(Move(player_id="p1", action="roll_dice", payload={"die1": 1, "die2": 1}))
        self.assertEqual(state.board["positions"]["p1"], 1)
        self.assertEqual(state.board["money"]["p1"], 1700)

    def test_go_to_jail_tile_sends_player_to_jail(self):
        game = MonopolyGame()
        game.start(self.players)
        game.state.board["positions"]["p1"] = 28
        state = game.apply_move(Move(player_id="p1", action="roll_dice", payload={"die1": 1, "die2": 1}))
        self.assertEqual(state.board["positions"]["p1"], 10)
        self.assertEqual(state.board["jail_turns"]["p1"], 2)
        self.assertEqual(state.current_player_id, "p2")

    def test_trade_offer_and_accept_transfers_cash(self):
        game = MonopolyGame()
        game.start(self.players)

        game.apply_move(Move(player_id="p1", action="offer_trade", payload={"to_player_id": "p2", "offer_cash": 100}))
        game.apply_move(Move(player_id="p1", action="end_turn"))

        state = game.apply_move(Move(player_id="p2", action="accept_trade", payload={"offer_index": 0}))
        self.assertEqual(state.board["money"]["p1"], 1400)
        self.assertEqual(state.board["money"]["p2"], 1600)

    def test_store_can_retrieve_saved_game(self):
        game = MonopolyGame()
        state = game.start(self.players)
        store = InMemoryGameStore()
        store.save(game)
        loaded = store.get(state.game_id)
        self.assertEqual(loaded.state.game_id, state.game_id)


if __name__ == "__main__":
    unittest.main()
