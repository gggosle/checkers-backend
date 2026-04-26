from dataclasses import replace

from .board_validation import get_piece
from .constants import GameConfig
from .entities import Board, Checker, GameState, Move, Position


def check_promotion(piece: Checker, target_row: int) -> bool:
    if piece.is_king:
        return False
    return (
        (piece.direction == 1 and target_row == GameConfig.BOARD_SIZE - 1)
        or (piece.direction == -1 and target_row == 0)
    )


def apply_move(state: GameState, from_pos: Position, to_move: Move) -> GameState:
    from .move_calculator import has_jump_available

    piece = get_piece(state.board, from_pos.row, from_pos.col)
    if not piece:
        return state

    new_board = [row[:] for row in state.board]

    is_jump = to_move.type == 'jump'
    is_promoted = check_promotion(piece, to_move.row)

    moved_piece = replace(piece, row=to_move.row, col=to_move.col)

    new_board[from_pos.row][from_pos.col] = None
    new_board[to_move.row][to_move.col] = moved_piece

    if is_jump and to_move.captured:
        new_board[to_move.captured.row][to_move.captured.col] = None

    if is_promoted:
        moved_piece.is_king = True

    if is_jump and not is_promoted and has_jump_available(new_board, to_move.row, to_move.col):
        return replace(
            state,
            board=new_board,
            must_jump_piece=Position(row=to_move.row, col=to_move.col),
        )

    return replace(
        state,
        board=new_board,
        must_jump_piece=None,
        current_player_id=next(p.id for p in state.players if p.id != state.current_player_id),
    )