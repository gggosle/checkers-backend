from __future__ import annotations
from typing import List, Optional
from .entities import Checker, Board, Move, Position, GameState, MoveType, Player
from .constants import GameConfig
from dataclasses import replace


def is_black_square(row: int, col: int) -> bool:
    return (row + col) % 2 == 1


def is_in_bounds(row: int, col: int) -> bool:
    return 0 <= row < GameConfig.BOARD_SIZE and 0 <= col < GameConfig.BOARD_SIZE


def get_piece(board: Board, row: int, col: int) -> Optional[Checker]:
    if not is_in_bounds(row, col):
        return None
    return board[row][col]


def get_possible_directions(piece: Checker) -> List[dict]:
    directions = [1, -1] if piece.is_king else [piece.direction]
    moves = []
    for dr in directions:
        for dc in [1, -1]:
            moves.append({'dr': dr, 'dc': dc})
    return moves


def try_calculate_jump(board: Board, piece: Checker, target_piece: Checker, dr: int, dc: int) -> \
        Optional[Move]:
    if target_piece.color == piece.color:
        return None

    jump_row = target_piece.row + dr
    jump_col = target_piece.col + dc

    if is_in_bounds(jump_row, jump_col) and not get_piece(board, jump_row, jump_col):
        return Move(
            row=jump_row,
            col=jump_col,
            type=MoveType.JUMP,
            captured=Position(row=target_piece.row, col=target_piece.col)
        )
    return None


def calculate_target_move(board: Board, piece: Checker, row: int, col: int, dr: int, dc: int) -> \
        Optional[Move]:
    target_row = row + dr
    target_col = col + dc

    if not is_in_bounds(target_row, target_col):
        return None

    target_piece = get_piece(board, target_row, target_col)
    if not target_piece:
        return Move(row=target_row, col=target_col, type=MoveType.MOVE, captured=None)

    return try_calculate_jump(board, piece, target_piece, dr, dc)


def has_jump_available(board: Board, row: int, col: int) -> bool:
    piece = get_piece(board, row, col)
    if not piece:
        return False

    directions = get_possible_directions(piece)
    for d in directions:
        move = calculate_target_move(board, piece, row, col, d['dr'], d['dc'])
        if move and move.type == MoveType.JUMP:
            return True
    return False


def calculate_potential_moves(board: Board, row: int, col: int) -> List[Move]:
    piece = get_piece(board, row, col)
    if not piece:
        return []

    moves: List[Move] = []
    directions = get_possible_directions(piece)

    for d in directions:
        move = calculate_target_move(board, piece, row, col, d['dr'], d['dc'])
        if move:
            moves.append(move)
    return moves


def get_valid_moves(
        board: Board,
        player_move_dir: int,
        must_jump_piece: Optional[Position],
        has_jumps_available: bool,
        row: int,
        col: int
) -> List[Move]:
    piece = get_piece(board, row, col)
    if not piece or piece.direction != player_move_dir:
        return []

    if must_jump_piece and (must_jump_piece.row != row or must_jump_piece.col != col):
        return []

    moves = calculate_potential_moves(board, row, col)

    if has_jumps_available:
        return [move for move in moves if move.type == MoveType.JUMP]

    return moves

def any_player_jumps_available(board: Board, player_move_dir: int) -> bool:
    for r in range(GameConfig.BOARD_SIZE):
        for c in range(GameConfig.BOARD_SIZE):
            piece = get_piece(board, r, c)
            if piece and piece.direction == player_move_dir:
                if has_jump_available(board, r, c):
                    return True
    return False


def has_any_valid_moves(
        board: Board,
        player_move_dir: int,
        must_jump_piece: Position | None,
        has_jumps_available: bool
) -> bool:
    for r in range(GameConfig.BOARD_SIZE):
        for c in range(GameConfig.BOARD_SIZE):
            piece = get_piece(board, r, c)
            if piece and piece.direction == player_move_dir:
                moves = get_valid_moves(
                    board, player_move_dir, must_jump_piece, has_jumps_available, r, c
                )
                if len(moves) > 0:
                    return True
    return False


def check_promotion(piece: Checker, target_row: int) -> bool:
    if piece.is_king:
        return False
    return (piece.direction == 1 and target_row == GameConfig.BOARD_SIZE - 1) or \
        (piece.direction == -1 and target_row == 0)


def apply_move(state: GameState, from_pos: Position, to_move: Move) -> GameState:
    piece = get_piece(state.board, from_pos.row, from_pos.col)
    if not piece:
        return state

    new_board = [row[:] for row in state.board]

    is_jump = to_move.type == MoveType.JUMP
    is_promoted = check_promotion(piece, to_move.row)

    moved_piece = replace(piece, row=to_move.row, col=to_move.col)

    new_board[from_pos.row][from_pos.col] = None
    new_board[to_move.row][to_move.col] = moved_piece

    if is_jump and to_move.captured:
        new_board[to_move.captured.row][to_move.captured.col] = None

    if is_promoted:
        moved_piece.is_king = True

    if is_jump and not is_promoted:
        if has_jump_available(new_board, to_move.row, to_move.col):
            return replace(
                state,
                board=new_board,
                must_jump_piece=Position(row=to_move.row, col=to_move.col),
                selected_piece=None,
            )

    next_player = next(p for p in state.players if p.id != state.current_player.id)

    return replace(
        state,
        board=new_board,
        must_jump_piece=None,
        current_player=next_player,
        selected_piece=None,
    )

def calculate_winner(state: GameState) -> Player | None:
    jumps_available = any_player_jumps_available(state.board, state.current_player.move_dir)

    can_current_player_move = has_any_valid_moves(
        state.board,
        state.current_player.move_dir,
        state.must_jump_piece,
        jumps_available
    )

    if not can_current_player_move:
        return next((p for p in state.players if p.id != state.current_player.id), None)

    return None
