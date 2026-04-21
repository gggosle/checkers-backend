from dataclasses import dataclass
from typing import Optional
from .constants import Color, MoveType

@dataclass
class Player:
    id: int
    name: str
    color: Color
    move_dir: int

@dataclass
class Checker:
    id: str
    color: Color
    row: int
    col: int
    direction: int
    is_king: bool = False


@dataclass
class Position:
    row: int
    col: int


@dataclass
class MoveRecord:
    player_id: int
    from_pos: Position
    to_pos: Position
    is_jump: bool
    promoted_to_king: bool


@dataclass
class Move:
    row: int
    col: int
    type: MoveType
    captured: Optional[Position]


Board = list[list[Optional[Checker]]]

@dataclass
class GameState:
    board: Board
    players: list[Player]
    current_player_id: int
    must_jump_piece: Optional[Position]

    @property
    def current_player(self) -> Player:
        return next(p for p in self.players if p.id == self.current_player_id)