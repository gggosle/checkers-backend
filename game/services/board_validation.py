from __future__ import annotations

from typing import Optional

from .constants import GameConfig
from .entities import Board, Checker, Position


def is_black_square(row: int, col: int) -> bool:
    return (row + col) % 2 == 1


def is_in_bounds(row: int, col: int) -> bool:
    return 0 <= row < GameConfig.BOARD_SIZE and 0 <= col < GameConfig.BOARD_SIZE


def get_piece(board: Board, row: int, col: int) -> Optional[Checker]:
    if not is_in_bounds(row, col):
        return None
    return board[row][col]