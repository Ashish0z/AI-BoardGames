from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Dict

from ..core.base import BoardGame
from ..core.models import Move
from .ollama import OllamaClient


class AdaptiveAIStrategyService:
    def __init__(self, llm_client: OllamaClient) -> None:
        self.llm_client = llm_client

    def choose_move(self, game: BoardGame, player_id: str) -> Move:
        if not game.state:
            raise ValueError("Game has not started")

        available = game.available_moves(player_id)
        player = next((p for p in game.state.players if p.id == player_id), None)
        if player is None:
            raise ValueError("Unknown player")

        prompt = (
            "You are an AI board game player. "
            f"Game type: {game.game_type}. "
            f"Player skill level from 0.0 beginner to 1.0 expert: {player.skill_level}. "
            f"Current game state: {json.dumps(game.state.board)}. "
            f"Available moves: {json.dumps(available)}. "
            "Return only a JSON object with keys: action, payload, reason."
        )

        try:
            raw = self.llm_client.chat(prompt)
            data: Dict[str, object] = json.loads(raw)
            action = str(data.get("action", available[0]["action"]))
            payload = data.get("payload", {})
            reason = str(data.get("reason", ""))
            if action not in {move["action"] for move in available}:
                action = str(available[0]["action"])
            if not isinstance(payload, dict):
                payload = {}
            return Move(player_id=player_id, action=action, payload=payload, reason=reason)
        except (JSONDecodeError, TypeError, ValueError, RuntimeError):
            fallback = available[0]
            return Move(
                player_id=player_id,
                action=str(fallback["action"]),
                payload={},
                reason="Fallback move because LLM output was unavailable or invalid.",
            )


class GameCoachService:
    def __init__(self, llm_client: OllamaClient) -> None:
        self.llm_client = llm_client

    def answer(self, game: BoardGame, message: str) -> str:
        state = json.dumps(game.state.board if game.state else {})
        prompt = (
            f"You are a helpful {game.game_type} coach. "
            f"Current state: {state}. "
            "Give concise strategy guidance for the player's question: "
            f"{message}"
        )
        return self.llm_client.chat(prompt)
