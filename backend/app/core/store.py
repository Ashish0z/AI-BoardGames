from __future__ import annotations

from typing import Dict

from .base import BoardGame


class InMemoryGameStore:
    def __init__(self) -> None:
        self._games: Dict[str, BoardGame] = {}

    def save(self, game: BoardGame) -> None:
        if not game.state:
            raise ValueError("Cannot save game without state")
        self._games[game.state.game_id] = game

    def get(self, game_id: str) -> BoardGame:
        if game_id not in self._games:
            raise KeyError(f"Game {game_id} not found")
        return self._games[game_id]
