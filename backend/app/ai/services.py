from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Dict

from ..core.base import BoardGame
from ..core.models import Move
from ..logging_utils import get_debug_logger
from .ollama import OllamaClient

DEFAULT_MONOPOLY_AI_PROMPT = """
You are an expert Monopoly player making one legal move for your current turn.
Priorities:
1) Always return only valid actions from the provided available moves.
2) Prefer economically sound play: buy strong properties when affordable, avoid avoidable penalties.
3) Respect current board state, ownership, cash, and pending actions.
4) Never invent fields, tiles, or actions that are not present.
5) If there is pending buy_or_skip, decide between buy_property or skip_purchase only.
6) If in jail, follow jail rules and choose from legal jail actions.
7) Keep reasons concise and tied to current game state.
Output format must be a JSON object with keys:
  - action: string
  - payload: object
  - reason: string
No extra text outside JSON.
""".strip()

DEFAULT_COACH_PROMPT = "You are a helpful Monopoly coach giving concise strategy guidance."


class AdaptiveAIStrategyService:
    def __init__(self, llm_client: OllamaClient) -> None:
        self.llm_client = llm_client
        self.logger = get_debug_logger()

    def _base_prompt(self, game: BoardGame) -> str:
        if not game.state:
            return DEFAULT_MONOPOLY_AI_PROMPT
        configured = str(game.state.metadata.get("ai_prompt", "")).strip()
        if configured:
            return configured
        if game.game_type == "monopoly":
            return DEFAULT_MONOPOLY_AI_PROMPT
        return "You are an AI board game player. Return only legal JSON move output."

    def choose_move(self, game: BoardGame, player_id: str) -> Move:
        if not game.state:
            raise ValueError("Game has not started")

        available = game.available_moves(player_id)
        player = next((p for p in game.state.players if p.id == player_id), None)
        if player is None:
            raise ValueError("Unknown player")

        prompt = (
            f"{self._base_prompt(game)} "
            f"Game type: {game.game_type}. "
            f"Player skill level from 0.0 beginner to 1.0 expert: {player.skill_level}. "
            f"Current game state: {json.dumps(game.state.board)}. "
            f"Available moves: {json.dumps(available)}. "
            "Return only a JSON object with keys: action, payload, reason."
        )
        self.logger.debug(
            "ai_move_prompt game_id=%s player_id=%s prompt=%s",
            game.state.game_id,
            player_id,
            prompt,
        )

        try:
            raw = self.llm_client.chat(prompt)
            self.logger.debug("ai_move_response game_id=%s player_id=%s response=%s", game.state.game_id, player_id, raw)
            data: Dict[str, object] = json.loads(raw)
            action = str(data.get("action", available[0]["action"]))
            payload = data.get("payload", {})
            reason = str(data.get("reason", ""))
            if action not in {move["action"] for move in available}:
                action = str(available[0]["action"])
            if not isinstance(payload, dict):
                payload = {}
            return Move(player_id=player_id, action=action, payload=payload, reason=reason)
        except (JSONDecodeError, TypeError, ValueError, RuntimeError) as exc:
            self.logger.debug("ai_move_fallback game_id=%s player_id=%s error=%s", game.state.game_id, player_id, exc)
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
        self.logger = get_debug_logger()

    def answer(self, game: BoardGame, message: str) -> str:
        state = json.dumps(game.state.board if game.state else {})
        prompt_prefix = DEFAULT_COACH_PROMPT
        if game.state:
            configured = str(game.state.metadata.get("coach_prompt", "")).strip()
            if configured:
                prompt_prefix = configured
        prompt = (
            f"{prompt_prefix} "
            f"Current state: {state}. "
            "Give concise strategy guidance for the player's question: "
            f"{message}"
        )
        self.logger.debug(
            "coach_prompt game_id=%s prompt=%s",
            game.state.game_id if game.state else "unknown",
            prompt,
        )
        response = self.llm_client.chat(prompt)
        self.logger.debug(
            "coach_response game_id=%s response=%s",
            game.state.game_id if game.state else "unknown",
            response,
        )
        return response
