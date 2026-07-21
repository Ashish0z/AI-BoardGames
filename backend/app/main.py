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


class PlayerInput(BaseModel):
    id: str
    name: str
    is_human: bool = False
    skill_level: float = Field(default=0.5, ge=0.0, le=1.0)


class CreateGameInput(BaseModel):
    game_type: str
    players: List[PlayerInput]


class MoveInput(BaseModel):
    player_id: str
    action: str
    payload: Dict[str, object] = Field(default_factory=dict)
    reason: str = ""


class ChatInput(BaseModel):
    player_id: Optional[str] = None
    message: str


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
        store.save(game)
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
        return {"state": state.__dict__}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/games/{game_id}/ai-move")
def apply_ai_move(game_id: str, player_id: str) -> Dict[str, object]:
    try:
        game = store.get(game_id)
        move = ai_service.choose_move(game, player_id)
        state = game.apply_move(move)
        return {"move": move.__dict__, "state": state.__dict__}
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/games/{game_id}/chat")
def chat(game_id: str, payload: ChatInput) -> Dict[str, object]:
    try:
        game = store.get(game_id)
        answer = coach_service.answer(game, payload.message)
        return {"answer": answer}
    except (KeyError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
