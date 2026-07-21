from __future__ import annotations

from random import randint
from typing import Dict, List

from ...core.base import BoardGame
from ...core.models import GameState, Move, PlayerProfile


class MonopolyGame(BoardGame):
    def __init__(self) -> None:
        super().__init__(game_type="monopoly")

    def initial_board(self, players: List[PlayerProfile]) -> Dict[str, object]:
        return {
            "positions": {player.id: 0 for player in players},
            "money": {player.id: 1500 for player in players},
            "board_size": 40,
        }

    def available_moves(self, player_id: str) -> List[Dict[str, object]]:
        self.validate_move_turn(player_id)
        return [
            {"action": "roll_dice", "description": "Roll and move forward"},
            {"action": "end_turn", "description": "Pass turn without moving"},
        ]

    def apply_move(self, move: Move) -> GameState:
        self.validate_move_turn(move.player_id)
        if not self.state:
            raise ValueError("Game has not started")

        if move.action == "roll_dice":
            roll = int(move.payload.get("roll", randint(1, 6) + randint(1, 6)))
            if roll < 1 or roll > 12:
                raise ValueError("Invalid roll value")
            positions = self.state.board["positions"]
            money = self.state.board["money"]
            board_size = int(self.state.board["board_size"])
            current = int(positions[move.player_id])
            updated = (current + roll) % board_size
            if current + roll >= board_size:
                money[move.player_id] = int(money[move.player_id]) + 200
            positions[move.player_id] = updated
        elif move.action != "end_turn":
            raise ValueError(f"Unsupported action '{move.action}'")

        self.state.move_log.append(
            {
                "player_id": move.player_id,
                "action": move.action,
                "payload": move.payload,
                "reason": move.reason,
            }
        )
        self._advance_turn()
        return self.state
