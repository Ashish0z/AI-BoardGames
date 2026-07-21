from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List
from uuid import uuid4

from .models import GameState, Move, PlayerProfile


class BoardGame(ABC):
    game_type: str

    def __init__(self, game_type: str) -> None:
        self.game_type = game_type
        self.state: GameState | None = None

    def start(self, players: List[PlayerProfile]) -> GameState:
        if len(players) < 2:
            raise ValueError("At least two players are required")
        self.state = GameState(
            game_id=str(uuid4()),
            game_type=self.game_type,
            players=players,
            current_player_id=players[0].id,
            board=self.initial_board(players),
            metadata={"turn": 1},
        )
        return self.state

    @abstractmethod
    def initial_board(self, players: List[PlayerProfile]) -> Dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def available_moves(self, player_id: str) -> List[Dict[str, object]]:
        raise NotImplementedError

    @abstractmethod
    def apply_move(self, move: Move) -> GameState:
        raise NotImplementedError

    def validate_move_turn(self, player_id: str) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        if self.state.current_player_id != player_id:
            raise ValueError("It is not this player's turn")

    def _advance_turn(self) -> None:
        if not self.state:
            raise ValueError("Game has not started")
        idx = next(i for i, p in enumerate(self.state.players) if p.id == self.state.current_player_id)
        next_idx = (idx + 1) % len(self.state.players)
        self.state.current_player_id = self.state.players[next_idx].id
        self.state.metadata["turn"] = int(self.state.metadata.get("turn", 1)) + 1
