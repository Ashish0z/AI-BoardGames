from __future__ import annotations

from random import randint
from typing import Dict, List

from ...core.base import BoardGame
from ...core.models import GameState, Move, PlayerProfile


class MonopolyGame(BoardGame):
    def __init__(self) -> None:
        super().__init__(game_type="monopoly")
        self._chance_index = 0
        self._community_index = 0
        self._chance_cards = [
            {"kind": "money", "amount": 150, "message": "Bank pays you dividend of $150"},
            {"kind": "money", "amount": -15, "message": "Pay poor tax of $15"},
            {"kind": "move", "position": 0, "message": "Advance to GO"},
            {"kind": "move_relative", "steps": -3, "message": "Go back 3 spaces"},
            {"kind": "go_to_jail", "message": "Go directly to Jail"},
        ]
        self._community_cards = [
            {"kind": "money", "amount": 200, "message": "Income tax refund. Collect $200"},
            {"kind": "money", "amount": -100, "message": "Hospital fees. Pay $100"},
            {"kind": "money", "amount": 50, "message": "From sale of stock you get $50"},
            {"kind": "move", "position": 0, "message": "Advance to GO"},
        ]

    def start(self, players: List[PlayerProfile]) -> GameState:
        state = super().start(players)
        state.metadata["has_rolled"] = False
        return state

    def initial_board(self, players: List[PlayerProfile]) -> Dict[str, object]:
        return {
            "positions": {player.id: 0 for player in players},
            "money": {player.id: 1500 for player in players},
            "board_size": 40,
            "tiles": self._build_tiles(),
            "ownership": {},
            "properties_by_player": {player.id: [] for player in players},
            "jail_turns": {player.id: 0 for player in players},
            "pending_action": None,
            "trade_offers": [],
            "last_event": "Game started",
        }

    def available_moves(self, player_id: str) -> List[Dict[str, object]]:
        self.validate_move_turn(player_id)
        if not self.state:
            raise ValueError("Game has not started")

        pending = self.state.board["pending_action"]
        if pending and pending.get("player_id") == player_id:
            if pending.get("type") == "buy_or_skip":
                return [
                    {"action": "buy_property", "description": "Buy current property"},
                    {"action": "skip_purchase", "description": "Skip property purchase"},
                ]

        responses = self._open_offers_for(player_id)
        if responses:
            return [
                {"action": "accept_trade", "description": "Accept incoming trade"},
                {"action": "decline_trade", "description": "Decline incoming trade"},
            ]

        jail_turns = int(self.state.board["jail_turns"][player_id])
        if jail_turns > 0:
            return [
                {"action": "pay_bail", "description": "Pay $50 to leave jail"},
                {"action": "roll_dice", "description": "Attempt doubles to leave jail"},
                {"action": "end_turn", "description": "Stay in jail and end turn"},
            ]

        moves = [{"action": "offer_trade", "description": "Offer a trade to another player"}]
        if not bool(self.state.metadata.get("has_rolled", False)):
            moves.append({"action": "roll_dice", "description": "Roll and move forward"})
        moves.append({"action": "end_turn", "description": "Finish your turn"})
        return moves

    def apply_move(self, move: Move) -> GameState:
        self.validate_move_turn(move.player_id)
        if not self.state:
            raise ValueError("Game has not started")

        action = move.action
        if action == "roll_dice":
            self._handle_roll(move)
        elif action == "buy_property":
            self._handle_buy(move.player_id)
        elif action == "skip_purchase":
            self._handle_skip_purchase(move.player_id)
        elif action == "offer_trade":
            self._handle_offer_trade(move)
        elif action == "accept_trade":
            self._handle_accept_trade(move)
        elif action == "decline_trade":
            self._handle_decline_trade(move)
        elif action == "pay_bail":
            self._handle_pay_bail(move.player_id)
        elif action == "end_turn":
            self._handle_end_turn(move.player_id)
        else:
            raise ValueError(f"Unsupported action '{action}'")

        self.state.move_log.append(
            {
                "player_id": move.player_id,
                "action": move.action,
                "payload": move.payload,
                "reason": move.reason,
            }
        )
        return self.state

    def _build_tiles(self) -> List[Dict[str, object]]:
        return [
            {"index": 0, "name": "GO", "type": "go"},
            {"index": 1, "name": "Mediterranean Avenue", "type": "property", "price": 60, "rent": 2},
            {"index": 2, "name": "Community Chest", "type": "community_chest"},
            {"index": 3, "name": "Baltic Avenue", "type": "property", "price": 60, "rent": 4},
            {"index": 4, "name": "Income Tax", "type": "tax", "amount": 200},
            {"index": 5, "name": "Reading Railroad", "type": "railroad", "price": 200, "rent": 25},
            {"index": 6, "name": "Oriental Avenue", "type": "property", "price": 100, "rent": 6},
            {"index": 7, "name": "Chance", "type": "chance"},
            {"index": 8, "name": "Vermont Avenue", "type": "property", "price": 100, "rent": 6},
            {"index": 9, "name": "Connecticut Avenue", "type": "property", "price": 120, "rent": 8},
            {"index": 10, "name": "Jail / Just Visiting", "type": "jail"},
            {"index": 11, "name": "St. Charles Place", "type": "property", "price": 140, "rent": 10},
            {"index": 12, "name": "Electric Company", "type": "utility", "price": 150, "rent": 20},
            {"index": 13, "name": "States Avenue", "type": "property", "price": 140, "rent": 10},
            {"index": 14, "name": "Virginia Avenue", "type": "property", "price": 160, "rent": 12},
            {"index": 15, "name": "Pennsylvania Railroad", "type": "railroad", "price": 200, "rent": 25},
            {"index": 16, "name": "St. James Place", "type": "property", "price": 180, "rent": 14},
            {"index": 17, "name": "Community Chest", "type": "community_chest"},
            {"index": 18, "name": "Tennessee Avenue", "type": "property", "price": 180, "rent": 14},
            {"index": 19, "name": "New York Avenue", "type": "property", "price": 200, "rent": 16},
            {"index": 20, "name": "Free Parking", "type": "free_parking"},
            {"index": 21, "name": "Kentucky Avenue", "type": "property", "price": 220, "rent": 18},
            {"index": 22, "name": "Chance", "type": "chance"},
            {"index": 23, "name": "Indiana Avenue", "type": "property", "price": 220, "rent": 18},
            {"index": 24, "name": "Illinois Avenue", "type": "property", "price": 240, "rent": 20},
            {"index": 25, "name": "B. & O. Railroad", "type": "railroad", "price": 200, "rent": 25},
            {"index": 26, "name": "Atlantic Avenue", "type": "property", "price": 260, "rent": 22},
            {"index": 27, "name": "Ventnor Avenue", "type": "property", "price": 260, "rent": 22},
            {"index": 28, "name": "Water Works", "type": "utility", "price": 150, "rent": 20},
            {"index": 29, "name": "Marvin Gardens", "type": "property", "price": 280, "rent": 24},
            {"index": 30, "name": "Go To Jail", "type": "go_to_jail"},
            {"index": 31, "name": "Pacific Avenue", "type": "property", "price": 300, "rent": 26},
            {"index": 32, "name": "North Carolina Avenue", "type": "property", "price": 300, "rent": 26},
            {"index": 33, "name": "Community Chest", "type": "community_chest"},
            {"index": 34, "name": "Pennsylvania Avenue", "type": "property", "price": 320, "rent": 28},
            {"index": 35, "name": "Short Line", "type": "railroad", "price": 200, "rent": 25},
            {"index": 36, "name": "Chance", "type": "chance"},
            {"index": 37, "name": "Park Place", "type": "property", "price": 350, "rent": 35},
            {"index": 38, "name": "Luxury Tax", "type": "tax", "amount": 100},
            {"index": 39, "name": "Boardwalk", "type": "property", "price": 400, "rent": 50},
        ]

    def _handle_roll(self, move: Move) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        if bool(self.state.metadata.get("has_rolled", False)):
            raise ValueError("You already rolled this turn")

        die1, die2 = self._resolve_dice(move.payload)
        roll = die1 + die2
        player_id = move.player_id
        jail_turns = int(self.state.board["jail_turns"][player_id])

        if jail_turns > 0:
            if die1 == die2:
                self.state.board["jail_turns"][player_id] = 0
                self._move_player(player_id, roll)
                self._apply_tile_effect(player_id)
                self.state.board["last_event"] = f"{player_id} rolled doubles and left jail"
                self.state.metadata["has_rolled"] = True
                return
            self.state.board["jail_turns"][player_id] = max(0, jail_turns - 1)
            self.state.board["last_event"] = f"{player_id} failed to roll doubles and remains in jail"
            self._finish_turn()
            return

        self._move_player(player_id, roll)
        self._apply_tile_effect(player_id)
        self.state.metadata["has_rolled"] = True

    def _resolve_dice(self, payload: Dict[str, object]) -> tuple[int, int]:
        die1 = payload.get("die1")
        die2 = payload.get("die2")
        if die1 is None or die2 is None:
            return randint(1, 6), randint(1, 6)
        first = int(die1)
        second = int(die2)
        if first < 1 or first > 6 or second < 1 or second > 6:
            raise ValueError("Invalid dice values")
        return first, second

    def _move_player(self, player_id: str, roll: int) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        positions = self.state.board["positions"]
        money = self.state.board["money"]
        board_size = int(self.state.board["board_size"])
        current = int(positions[player_id])
        updated = (current + roll) % board_size
        if current + roll >= board_size:
            money[player_id] = int(money[player_id]) + 200
        positions[player_id] = updated
        self.state.board["last_event"] = f"{player_id} moved to tile {updated}"

    def _apply_tile_effect(self, player_id: str) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        position = int(self.state.board["positions"][player_id])
        tile = self.state.board["tiles"][position]
        tile_type = str(tile["type"])

        if tile_type in {"property", "railroad", "utility"}:
            self._resolve_purchasable_tile(player_id, tile)
            return

        if tile_type == "tax":
            amount = int(tile["amount"])
            self.state.board["money"][player_id] = int(self.state.board["money"][player_id]) - amount
            self.state.board["last_event"] = f"{player_id} paid tax of ${amount}"
            return

        if tile_type == "chance":
            card = self._chance_cards[self._chance_index % len(self._chance_cards)]
            self._chance_index += 1
            self._apply_card(player_id, card)
            return

        if tile_type == "community_chest":
            card = self._community_cards[self._community_index % len(self._community_cards)]
            self._community_index += 1
            self._apply_card(player_id, card)
            return

        if tile_type == "go_to_jail":
            self.state.board["positions"][player_id] = 10
            self.state.board["jail_turns"][player_id] = 2
            self.state.board["last_event"] = f"{player_id} sent to jail"
            self._finish_turn()
            return

        self.state.board["last_event"] = f"{player_id} landed on {tile['name']}"

    def _resolve_purchasable_tile(self, player_id: str, tile: Dict[str, object]) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        ownership = self.state.board["ownership"]
        tile_index = int(tile["index"])
        owner = ownership.get(str(tile_index))

        if owner is None:
            self.state.board["pending_action"] = {
                "type": "buy_or_skip",
                "player_id": player_id,
                "tile_index": tile_index,
                "price": int(tile["price"]),
            }
            self.state.board["last_event"] = f"{player_id} can buy {tile['name']}"
            return

        if owner != player_id:
            rent = int(tile["rent"])
            self.state.board["money"][player_id] = int(self.state.board["money"][player_id]) - rent
            self.state.board["money"][owner] = int(self.state.board["money"][owner]) + rent
            self.state.board["last_event"] = f"{player_id} paid ${rent} rent to {owner}"

    def _handle_buy(self, player_id: str) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        pending = self.state.board["pending_action"]
        if not pending or pending.get("type") != "buy_or_skip" or pending.get("player_id") != player_id:
            raise ValueError("No property purchase is pending")

        tile_index = int(pending["tile_index"])
        price = int(pending["price"])
        funds = int(self.state.board["money"][player_id])
        if funds < price:
            raise ValueError("Insufficient funds to buy property")

        self.state.board["money"][player_id] = funds - price
        self.state.board["ownership"][str(tile_index)] = player_id
        self.state.board["properties_by_player"][player_id].append(tile_index)
        tile_name = self.state.board["tiles"][tile_index]["name"]
        self.state.board["pending_action"] = None
        self.state.board["last_event"] = f"{player_id} bought {tile_name}"

    def _handle_skip_purchase(self, player_id: str) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        pending = self.state.board["pending_action"]
        if not pending or pending.get("type") != "buy_or_skip" or pending.get("player_id") != player_id:
            raise ValueError("No property purchase is pending")
        self.state.board["pending_action"] = None
        self.state.board["last_event"] = f"{player_id} skipped purchase"

    def _handle_offer_trade(self, move: Move) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        to_player_id = str(move.payload.get("to_player_id", "")).strip()
        if not to_player_id:
            raise ValueError("Trade offer requires 'to_player_id'")
        if to_player_id == move.player_id:
            raise ValueError("Cannot trade with self")

        known_player_ids = {player.id for player in self.state.players}
        if to_player_id not in known_player_ids:
            raise ValueError("Unknown trade target")

        offer = {
            "from_player_id": move.player_id,
            "to_player_id": to_player_id,
            "offer_cash": int(move.payload.get("offer_cash", 0)),
            "request_cash": int(move.payload.get("request_cash", 0)),
            "offer_property": move.payload.get("offer_property"),
            "request_property": move.payload.get("request_property"),
            "status": "open",
        }
        self.state.board["trade_offers"].append(offer)
        self.state.board["last_event"] = f"{move.player_id} offered trade to {to_player_id}"

    def _open_offers_for(self, player_id: str) -> List[Dict[str, object]]:
        if not self.state:
            return []
        offers = self.state.board["trade_offers"]
        return [offer for offer in offers if offer["to_player_id"] == player_id and offer["status"] == "open"]

    def _handle_accept_trade(self, move: Move) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        offers = self._open_offers_for(move.player_id)
        if not offers:
            raise ValueError("No open trade offers to accept")

        offer_index = int(move.payload.get("offer_index", 0))
        if offer_index < 0 or offer_index >= len(offers):
            raise ValueError("Invalid trade offer index")

        offer = offers[offer_index]
        proposer = str(offer["from_player_id"])
        accepter = str(offer["to_player_id"])
        self._apply_trade_transfer(proposer, accepter, offer)
        offer["status"] = "accepted"
        self.state.board["last_event"] = f"{accepter} accepted trade from {proposer}"

    def _handle_decline_trade(self, move: Move) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        offers = self._open_offers_for(move.player_id)
        if not offers:
            raise ValueError("No open trade offers to decline")
        offer_index = int(move.payload.get("offer_index", 0))
        if offer_index < 0 or offer_index >= len(offers):
            raise ValueError("Invalid trade offer index")
        offer = offers[offer_index]
        offer["status"] = "declined"
        self.state.board["last_event"] = f"{move.player_id} declined a trade offer"

    def _apply_trade_transfer(self, proposer: str, accepter: str, offer: Dict[str, object]) -> None:
        if not self.state:
            raise ValueError("Game has not started")

        offer_cash = int(offer.get("offer_cash", 0))
        request_cash = int(offer.get("request_cash", 0))
        if int(self.state.board["money"][proposer]) < offer_cash:
            raise ValueError("Trade proposer has insufficient cash")
        if int(self.state.board["money"][accepter]) < request_cash:
            raise ValueError("Trade accepter has insufficient cash")

        self.state.board["money"][proposer] = int(self.state.board["money"][proposer]) - offer_cash + request_cash
        self.state.board["money"][accepter] = int(self.state.board["money"][accepter]) + offer_cash - request_cash

        self._transfer_property(proposer, accepter, offer.get("offer_property"))
        self._transfer_property(accepter, proposer, offer.get("request_property"))

    def _transfer_property(self, from_player: str, to_player: str, property_index: object) -> None:
        if not self.state or property_index is None:
            return

        idx = int(property_index)
        ownership = self.state.board["ownership"]
        if ownership.get(str(idx)) != from_player:
            raise ValueError("Trade includes property not owned by expected player")

        ownership[str(idx)] = to_player
        if idx in self.state.board["properties_by_player"][from_player]:
            self.state.board["properties_by_player"][from_player].remove(idx)
        self.state.board["properties_by_player"][to_player].append(idx)

    def _apply_card(self, player_id: str, card: Dict[str, object]) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        kind = str(card["kind"])

        if kind == "money":
            self.state.board["money"][player_id] = int(self.state.board["money"][player_id]) + int(card["amount"])
            self.state.board["last_event"] = str(card["message"])
            return

        if kind == "move":
            current = int(self.state.board["positions"][player_id])
            target = int(card["position"])
            if target < current:
                self.state.board["money"][player_id] = int(self.state.board["money"][player_id]) + 200
            self.state.board["positions"][player_id] = target
            self.state.board["last_event"] = str(card["message"])
            self._apply_tile_effect(player_id)
            return

        if kind == "move_relative":
            steps = int(card["steps"])
            board_size = int(self.state.board["board_size"])
            current = int(self.state.board["positions"][player_id])
            target = (current + steps) % board_size
            self.state.board["positions"][player_id] = target
            self.state.board["last_event"] = str(card["message"])
            self._apply_tile_effect(player_id)
            return

        if kind == "go_to_jail":
            self.state.board["positions"][player_id] = 10
            self.state.board["jail_turns"][player_id] = 2
            self.state.board["last_event"] = str(card["message"])
            self._finish_turn()

    def _handle_pay_bail(self, player_id: str) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        jail_turns = int(self.state.board["jail_turns"][player_id])
        if jail_turns <= 0:
            raise ValueError("Player is not in jail")
        if int(self.state.board["money"][player_id]) < 50:
            raise ValueError("Insufficient funds to pay bail")

        self.state.board["money"][player_id] = int(self.state.board["money"][player_id]) - 50
        self.state.board["jail_turns"][player_id] = 0
        self.state.board["last_event"] = f"{player_id} paid bail"

    def _handle_end_turn(self, player_id: str) -> None:
        if not self.state:
            raise ValueError("Game has not started")

        pending = self.state.board["pending_action"]
        if pending and pending.get("player_id") == player_id:
            raise ValueError("Resolve pending action before ending turn")

        self._finish_turn()

    def _finish_turn(self) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        self.state.metadata["has_rolled"] = False
        self._advance_turn()
