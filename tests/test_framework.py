import unittest

from backend.app.core.models import Move, PlayerProfile
from backend.app.core.store import InMemoryGameStore
from backend.app.games.monopoly.game import MonopolyGame
from backend.app.main import CreateGameInput, PlayerInput, create_game


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

    def test_monopoly_tiles_include_group_and_rules_metadata(self):
        game = MonopolyGame()
        state = game.start(self.players)
        mediterranean = state.board["tiles"][1]
        chance = state.board["tiles"][7]
        self.assertEqual(mediterranean["color_group"], "brown")
        self.assertEqual(mediterranean["house_cost"], 50)
        self.assertTrue(mediterranean["rent_tiers"])
        self.assertIn("rule_text", chance)
        self.assertTrue(chance["outcomes"])

    def test_create_game_stores_prompt_overrides(self):
        payload = CreateGameInput(
            game_type="monopoly",
            players=[
                PlayerInput(id="p1", name="Human", is_human=True, skill_level=0.5),
                PlayerInput(id="p2", name="AI", is_human=False, skill_level=0.7),
            ],
            ai_prompt="custom ai prompt",
            coach_prompt="custom coach prompt",
        )
        created = create_game(payload)
        metadata = created["state"]["metadata"]
        self.assertEqual(metadata["ai_prompt"], "custom ai prompt")
        self.assertEqual(metadata["coach_prompt"], "custom coach prompt")

    def test_initial_board_has_new_fields(self):
        game = MonopolyGame()
        state = game.start(self.players)
        self.assertIn("mortgages", state.board)
        self.assertIn("houses", state.board)
        self.assertIn("monopolies_by_player", state.board)

    def test_mortgage_and_unmortgage_property(self):
        game = MonopolyGame()
        game.start(self.players)
        # Give p1 Baltic Avenue (index 3, price $60, mortgage value $30)
        game.state.board["ownership"]["3"] = "p1"
        game.state.board["properties_by_player"]["p1"].append(3)
        initial_cash = int(game.state.board["money"]["p1"])

        state = game.apply_move(Move(player_id="p1", action="mortgage_property", payload={"property_index": 3}))
        self.assertTrue(state.board["mortgages"].get("3"))
        self.assertEqual(state.board["money"]["p1"], initial_cash + 30)

        # Unmortgage: costs 55% of price = $33
        state = game.apply_move(Move(player_id="p1", action="unmortgage_property", payload={"property_index": 3}))
        self.assertFalse(state.board["mortgages"].get("3"))
        self.assertEqual(state.board["money"]["p1"], initial_cash + 30 - 33)

    def test_mortgaged_property_charges_no_rent(self):
        game = MonopolyGame()
        game.start(self.players)
        game.state.board["ownership"]["3"] = "p1"
        game.state.board["properties_by_player"]["p1"].append(3)
        game.state.board["mortgages"]["3"] = True

        game.apply_move(Move(player_id="p1", action="end_turn"))
        state = game.apply_move(Move(player_id="p2", action="roll_dice", payload={"die1": 1, "die2": 2}))
        # p2 should pay no rent since property is mortgaged
        self.assertEqual(state.board["money"]["p2"], 1500)
        self.assertEqual(state.board["money"]["p1"], 1500)

    def test_monopoly_detection_updates_after_buy(self):
        game = MonopolyGame()
        game.start(self.players)
        # Give p1 Mediterranean (index 1), then buy Baltic (index 3)
        game.state.board["ownership"]["1"] = "p1"
        game.state.board["properties_by_player"]["p1"].append(1)
        # Move p1 to Baltic and buy it
        game.state.board["positions"]["p1"] = 1
        state = game.apply_move(Move(player_id="p1", action="roll_dice", payload={"die1": 1, "die2": 1}))
        self.assertIsNotNone(state.board["pending_action"])
        state = game.apply_move(Move(player_id="p1", action="buy_property"))
        self.assertIn("brown", state.board["monopolies_by_player"]["p1"])

    def test_monopoly_doubles_rent(self):
        game = MonopolyGame()
        game.start(self.players)
        # Give p1 both brown properties
        game.state.board["ownership"]["1"] = "p1"
        game.state.board["ownership"]["3"] = "p1"
        game.state.board["properties_by_player"]["p1"] = [1, 3]
        game.state.board["monopolies_by_player"]["p1"] = ["brown"]

        game.apply_move(Move(player_id="p1", action="end_turn"))
        p2_cash_before = int(game.state.board["money"]["p2"])
        state = game.apply_move(Move(player_id="p2", action="roll_dice", payload={"die1": 1, "die2": 2}))
        # Baltic Avenue base rent is 4; doubled = 8
        self.assertEqual(state.board["money"]["p2"], p2_cash_before - 8)

    def test_buy_house_requires_monopoly(self):
        game = MonopolyGame()
        game.start(self.players)
        # p1 only owns one of the two brown properties — no monopoly
        game.state.board["ownership"]["1"] = "p1"
        game.state.board["properties_by_player"]["p1"].append(1)
        with self.assertRaises(ValueError):
            game.apply_move(Move(player_id="p1", action="buy_house", payload={"property_index": 1}))

    def test_buy_house_success_and_rent_tiers(self):
        game = MonopolyGame()
        game.start(self.players)
        # Give p1 full brown monopoly
        game.state.board["ownership"]["1"] = "p1"
        game.state.board["ownership"]["3"] = "p1"
        game.state.board["properties_by_player"]["p1"] = [1, 3]
        game.state.board["monopolies_by_player"]["p1"] = ["brown"]

        initial_cash = int(game.state.board["money"]["p1"])
        # Build house on Mediterranean (house_cost = 50)
        state = game.apply_move(Move(player_id="p1", action="buy_house", payload={"property_index": 1}))
        self.assertEqual(state.board["houses"].get("1"), 1)
        self.assertEqual(state.board["money"]["p1"], initial_cash - 50)

    def test_even_build_rule_enforced(self):
        game = MonopolyGame()
        game.start(self.players)
        game.state.board["ownership"]["1"] = "p1"
        game.state.board["ownership"]["3"] = "p1"
        game.state.board["properties_by_player"]["p1"] = [1, 3]
        game.state.board["monopolies_by_player"]["p1"] = ["brown"]
        # Build one house on Mediterranean
        game.apply_move(Move(player_id="p1", action="buy_house", payload={"property_index": 1}))
        # Trying to build a second on Mediterranean before Baltic has one should fail
        with self.assertRaises(ValueError):
            game.apply_move(Move(player_id="p1", action="buy_house", payload={"property_index": 1}))

    def test_accept_trade_move_includes_offer_details(self):
        game = MonopolyGame()
        game.start(self.players)
        game.apply_move(Move(player_id="p1", action="offer_trade", payload={"to_player_id": "p2", "offer_cash": 50}))
        game.apply_move(Move(player_id="p1", action="end_turn"))
        moves = game.available_moves("p2")
        accept_move = next((m for m in moves if m["action"] == "accept_trade"), None)
        self.assertIsNotNone(accept_move)
        self.assertIn("offer", accept_move)
        self.assertEqual(accept_move["offer"]["offer_cash"], 50)

    def test_trade_with_property_transfer(self):
        game = MonopolyGame()
        game.start(self.players)
        game.state.board["ownership"]["1"] = "p1"
        game.state.board["properties_by_player"]["p1"].append(1)
        game.apply_move(Move(player_id="p1", action="offer_trade", payload={
            "to_player_id": "p2",
            "offer_cash": 0,
            "offer_property": 1,
        }))
        game.apply_move(Move(player_id="p1", action="end_turn"))
        state = game.apply_move(Move(player_id="p2", action="accept_trade", payload={"offer_index": 0}))
        self.assertEqual(state.board["ownership"]["1"], "p2")
        self.assertIn(1, state.board["properties_by_player"]["p2"])
        self.assertNotIn(1, state.board["properties_by_player"]["p1"])


if __name__ == "__main__":
    unittest.main()
