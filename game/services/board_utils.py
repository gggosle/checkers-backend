from __future__ import annotations
from typing import List, Optional
from .game_rules import is_black_square
from .entities import Board, Checker, MoveEntry

def create_initial_board(board_size: int, piece_rows_count: int, move_dir_up: int, move_dir_down: int) -> Board:
    board: Board = []

    for row in range(board_size):
        row_array: List[Optional[Checker]] = []

        for col in range(board_size):
            if not is_black_square(row, col):
                row_array.append(None)
                continue

            stable_id = f"piece-{row}-{col}"

            if row < piece_rows_count:
                row_array.append(Checker(
                    id=stable_id,
                    color='white',
                    row=row,
                    col=col,
                    direction=move_dir_up,
                    is_king=False
                ))
            elif row >= board_size - piece_rows_count:
                row_array.append(Checker(
                    id=stable_id,
                    color='black',
                    row=row,
                    col=col,
                    direction=move_dir_down,
                    is_king=False
                ))
            else:
                row_array.append(None)
        board.append(row_array)

    return board


def calculate_initial_piece_count(board_size: int, rows_count: int) -> int:
    return (board_size * rows_count) // 2


def reconstruct_board(history: List[MoveEntry], board_size: int, piece_rows: int, dir_up: int, dir_down: int) -> Board:
    current_board = create_initial_board(board_size, piece_rows, dir_up, dir_down)

    for entry in history:
        piece = current_board[entry.from_pos.row][entry.from_pos.col]
        if not piece:
            continue

        piece.row = entry.to_pos.row
        piece.col = entry.to_pos.col

        current_board[entry.from_pos.row][entry.from_pos.col] = None
        current_board[entry.to_pos.row][entry.to_pos.col] = piece

        if entry.is_jump:
            captured_row = (entry.from_pos.row + entry.to_pos.row) // 2
            captured_col = (entry.from_pos.col + entry.to_pos.col) // 2
            current_board[captured_row][captured_col] = None

        if entry.promoted_to_king:
            piece.is_king = True

    return current_board