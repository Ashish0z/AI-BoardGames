from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .ai.ollama import OllamaClient
from .ai.services import AdaptiveAIStrategyService, GameCoachService
from .core.models import Move, PlayerProfile
from .core.store import InMemoryGameStore
from .games.monopoly.game import MonopolyGame
from .logging_utils import get_debug_logger


class PlayerInput(BaseModel):
    id: str
    name: str
    is_human: bool = False
    skill_level: float = Field(default=0.5, ge=0.0, le=1.0)


class CreateGameInput(BaseModel):
    game_type: str
    players: List[PlayerInput]
    ai_prompt: Optional[str] = None
    coach_prompt: Optional[str] = None


class MoveInput(BaseModel):
    player_id: str
    action: str
    payload: Dict[str, object] = Field(default_factory=dict)
    reason: str = ""


class ChatInput(BaseModel):
    player_id: Optional[str] = None
    message: str


class PromptUpdateInput(BaseModel):
    ai_prompt: Optional[str] = None
    coach_prompt: Optional[str] = None


app = FastAPI(title="AI Board Games Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = InMemoryGameStore()
llm_client = OllamaClient()
ai_service = AdaptiveAIStrategyService(llm_client)
coach_service = GameCoachService(llm_client)
debug_logger = get_debug_logger()
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
frontend_src = Path(__file__).resolve().parents[2] / "frontend"

if (frontend_dist / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="frontend-assets")


def build_game(game_type: str):
    if game_type == "monopoly":
        return MonopolyGame()
    raise ValueError(f"Unsupported game type '{game_type}'")


@app.get("/")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/ui")
def ui() -> FileResponse:
    ui_path = frontend_dist / "index.html"
    if not ui_path.exists():
        ui_path = frontend_src / "index.html"
    return FileResponse(ui_path)


@app.get("/games/types")
def game_types() -> Dict[str, object]:
    return {
        "games": [
            {"key": "monopoly", "label": "Monopoly", "enabled": True},
            {"key": "catan", "label": "Catan", "enabled": False},
            {"key": "chess", "label": "Chess", "enabled": False},
            {"key": "risk", "label": "Risk", "enabled": False},
        ]
    }


@app.post("/games")
def create_game(payload: CreateGameInput) -> Dict[str, object]:
    try:
        game = build_game(payload.game_type)
        state = game.start([
            PlayerProfile(
                id=player.id,
                name=player.name,
                is_human=player.is_human,
                skill_level=player.skill_level,
            )
            for player in payload.players
        ])
        ai_prompt = payload.ai_prompt.strip() if payload.ai_prompt else ""
        coach_prompt = payload.coach_prompt.strip() if payload.coach_prompt else ""
        if ai_prompt:
            state.metadata["ai_prompt"] = ai_prompt
        if coach_prompt:
            state.metadata["coach_prompt"] = coach_prompt
        store.save(game)
        debug_logger.debug(
            "create_game game_id=%s game_type=%s players=%s",
            state.game_id,
            state.game_type,
            [player.id for player in state.players],
        )
        return {"game_id": state.game_id, "state": state.__dict__}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/games/{game_id}")
def get_game(game_id: str) -> Dict[str, object]:
    try:
        game = store.get(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"game_id": game_id, "state": game.state.__dict__ if game.state else {}}


@app.get("/games/{game_id}/moves/{player_id}")
def get_moves(game_id: str, player_id: str) -> Dict[str, object]:
    try:
        game = store.get(game_id)
        return {"moves": game.available_moves(player_id)}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/games/{game_id}/move")
def apply_move(game_id: str, payload: MoveInput) -> Dict[str, object]:
    try:
        game = store.get(game_id)
        state = game.apply_move(
            Move(
                player_id=payload.player_id,
                action=payload.action,
                payload=payload.payload,
                reason=payload.reason,
            )
        )
        debug_logger.debug(
            "human_move game_id=%s player_id=%s action=%s payload=%s turn=%s last_event=%s",
            game_id,
            payload.player_id,
            payload.action,
            payload.payload,
            state.metadata.get("turn"),
            state.board.get("last_event"),
        )
        return {"state": state.__dict__}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/games/{game_id}/ai-move")
def apply_ai_move(game_id: str, player_id: str) -> Dict[str, object]:
    try:
        game = store.get(game_id)
        available = game.available_moves(player_id)
        if any(str(item.get("action")) == "roll_dice" for item in available):
            auto_roll = Move(
                player_id=player_id,
                action="roll_dice",
                payload={},
                reason="Automatic turn-start roll",
            )
            state = game.apply_move(auto_roll)
            debug_logger.debug(
                "ai_auto_roll game_id=%s player_id=%s turn=%s last_event=%s",
                game_id,
                player_id,
                state.metadata.get("turn"),
                state.board.get("last_event"),
            )
            if state.current_player_id != player_id:
                return {"move": auto_roll.__dict__, "state": state.__dict__}

        move = ai_service.choose_move(game, player_id)
        state = game.apply_move(move)
        debug_logger.debug(
            "ai_move game_id=%s player_id=%s action=%s payload=%s reason=%s turn=%s last_event=%s",
            game_id,
            player_id,
            move.action,
            move.payload,
            move.reason,
            state.metadata.get("turn"),
            state.board.get("last_event"),
        )
        return {"move": move.__dict__, "state": state.__dict__}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/games/{game_id}/chat")
def chat(game_id: str, payload: ChatInput) -> Dict[str, object]:
    try:
        game = store.get(game_id)
        answer = coach_service.answer(game, payload.message)
        debug_logger.debug(
            "chat game_id=%s player_id=%s message=%s answer=%s",
            game_id,
            payload.player_id or "human",
            payload.message,
            answer,
        )
        return {"answer": answer}
    except (KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/games/{game_id}/prompts")
def update_prompts(game_id: str, payload: PromptUpdateInput) -> Dict[str, object]:
    try:
        game = store.get(game_id)
        if not game.state:
            raise ValueError("Cannot update prompts: game state not initialized")
        if payload.ai_prompt is not None:
            game.state.metadata["ai_prompt"] = payload.ai_prompt.strip()
        if payload.coach_prompt is not None:
            game.state.metadata["coach_prompt"] = payload.coach_prompt.strip()
        debug_logger.debug(
            "update_prompts game_id=%s has_ai_prompt=%s has_coach_prompt=%s",
            game_id,
            bool(game.state.metadata.get("ai_prompt")),
            bool(game.state.metadata.get("coach_prompt")),
        )
        return {"state": game.state.__dict__}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
