from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class PlayerProfile:
    id: str
    name: str
    is_human: bool = False
    skill_level: float = 0.5


@dataclass
class Move:
    player_id: str
    action: str
    payload: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass
class GameState:
    game_id: str
    game_type: str
    players: List[PlayerProfile]
    current_player_id: str
    board: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    move_log: List[Dict[str, Any]] = field(default_factory=list)
