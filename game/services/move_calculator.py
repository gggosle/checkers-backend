from __future__ import annotations

from typing import Optional

from .board_validation import get_piece, is_in_bounds
from .constants import GameConfig
from .entities import Board, Checker, Move, Position


def get_possible_directions(piece: Checker) -> list[tuple[int, int]]:
    row_directions = (1, -1) if piece.is_king else (piece.direction,)
    return [(dr, dc) for dr in row_directions for dc in (1, -1)]


def try_calculate_jump(
    board: Board,
    piece: Checker,
    target_piece: Checker,
    dr: int,
    dc: int,
) -> Optional[Move]:
    if target_piece.color == piece.color:
        return None

    jump_row = target_piece.row + dr
    jump_col = target_piece.col + dc

    if is_in_bounds(jump_row, jump_col) and not get_piece(board, jump_row, jump_col):
        return Move(
            row=jump_row,
            col=jump_col,
            type='jump',
            captured=Position(row=target_piece.row, col=target_piece.col)
        )
    return None


def calculate_target_move(
    board: Board,
    piece: Checker,
    row: int,
    col: int,
    dr: int,
    dc: int,
) -> Optional[Move]:
    target_row = row + dr
    target_col = col + dc

    if not is_in_bounds(target_row, target_col):
        return None

    target_piece = get_piece(board, target_row, target_col)
    if not target_piece:
        return Move(row=target_row, col=target_col, type='move', captured=None)

    return try_calculate_jump(board, piece, target_piece, dr, dc)


def has_jump_available(board: Board, row: int, col: int) -> bool:
    piece = get_piece(board, row, col)
    if not piece:
        return False

    for dr, dc in get_possible_directions(piece):
        move = calculate_target_move(board, piece, row, col, dr, dc)
        if move and move.type == 'jump':
            return True
    return False


def calculate_potential_moves(board: Board, row: int, col: int) -> list[Move]:
    piece = get_piece(board, row, col)
    if not piece:
        return []

    moves: list[Move] = []
    for dr, dc in get_possible_directions(piece):
        move = calculate_target_move(board, piece, row, col, dr, dc)
        if move:
            moves.append(move)
    return moves


def get_valid_moves(
    board: Board,
    player_move_dir: int,
    must_jump_piece: Optional[Position],
    has_jumps_available: bool,
    row: int,
    col: int,
) -> list[Move]:
    piece = get_piece(board, row, col)
    if not piece or piece.direction != player_move_dir:
        return []

    if must_jump_piece and (must_jump_piece.row != row or must_jump_piece.col != col):
        return []

    moves = calculate_potential_moves(board, row, col)

    if has_jumps_available:
        return [move for move in moves if move.type == 'jump']

    return moves


def _serialize_move(move: Move) -> dict:
    return {
        'row': move.row,
        'col': move.col,
        'type': move.type,
        'captured': {'row': move.captured.row, 'col': move.captured.col} if move.captured else None,
    }


def _piece_moves_entry(row: int, col: int, moves: list[Move]) -> dict:
    return {
        'from_pos': {'row': row, 'col': col},
        'moves': [_serialize_move(move) for move in moves],
    }


def _must_jump_piece_moves(
    board: Board,
    player_move_dir: int,
    must_jump_piece: Position,
) -> list[dict]:
    moves = get_valid_moves(
        board, player_move_dir, must_jump_piece, has_jumps_available=True,
        row=must_jump_piece.row, col=must_jump_piece.col
    )
    if not moves:
        return []
    return [_piece_moves_entry(must_jump_piece.row, must_jump_piece.col, moves)]


def _iter_player_piece_positions(board: Board, player_move_dir: int):
    for row in range(GameConfig.BOARD_SIZE):
        for col in range(GameConfig.BOARD_SIZE):
            piece = get_piece(board, row, col)
            if piece and piece.direction == player_move_dir:
                yield row, col


def _collect_player_moves(board: Board, player_move_dir: int) -> tuple[list[dict], list[dict]]:
    all_moves, jump_moves = [], []
    for row, col in _iter_player_piece_positions(board, player_move_dir):
        moves = calculate_potential_moves(board, row, col)
        if not moves:
            continue
        all_moves.append(_piece_moves_entry(row, col, moves))
        jumps = [move for move in moves if move.type == 'jump']
        if jumps:
            jump_moves.append(_piece_moves_entry(row, col, jumps))
    return all_moves, jump_moves


def get_all_valid_moves(
    board: Board,
    player_move_dir: int,
    must_jump_piece: Optional[Position],
) -> list[dict]:
    if must_jump_piece:
        return _must_jump_piece_moves(board, player_move_dir, must_jump_piece)
    all_moves, jump_moves = _collect_player_moves(board, player_move_dir)
    return jump_moves if jump_moves else all_moves