from dataclasses import asdict

from django.db import transaction
from django.shortcuts import get_object_or_404

from game.models import Game, MoveEntry

from .board_utils import reconstruct_board
from .constants import GameConfig, GameRules
from .entities import Board, MoveRecord, Position
from .game_queries import state_from_model
from .move_calculator import get_all_valid_moves


def _move_record_from_entry(entry: MoveEntry) -> MoveRecord:
    return MoveRecord(
        player_id=entry.player_dir,
        from_pos=Position(row=entry.from_pos['row'], col=entry.from_pos['col']),
        to_pos=Position(row=entry.to_pos['row'], col=entry.to_pos['col']),
        is_jump=entry.is_jump,
        promoted_to_king=entry.is_promoted,
    )


def _calculate_must_jump_piece(last_move: MoveRecord | None, board: Board):
    from .move_calculator import has_jump_available

    if last_move and last_move.is_jump:
        if has_jump_available(board, last_move.to_pos.row, last_move.to_pos.col):
            return last_move.to_pos
    return None


def _get_ids_to_revert(game: Game, player_dir: int) -> list:
    ids = []
    for move in MoveEntry.objects.filter(game=game).order_by('-created_at'):
        if move.player_dir != player_dir:
            break
        ids.append(move.id)
    return ids


def _build_reverted_state_context(game: Game) -> tuple[MoveEntry | None, MoveRecord | None, Board]:
    moves = MoveEntry.objects.filter(game=game)
    history = [_move_record_from_entry(move) for move in moves]
    return moves.last(), history[-1] if history else None, reconstruct_board(
        history,
        GameConfig.BOARD_SIZE,
        GameRules.PIECE_ROWS_COUNT,
        GameRules.MOVE_DIR_UP,
        GameRules.MOVE_DIR_DOWN,
    )


def _apply_reverted_turn(game: Game, last_player_dir: int, last_move: MoveRecord | None, board: Board) -> None:
    game.board = [[asdict(cell) if cell else None for cell in row] for row in board]
    player = next(p for p in game.players if p['move_dir'] == last_player_dir)
    game.current_player_id = player['id']
    must_jump = _calculate_must_jump_piece(last_move, board)
    game.must_jump_piece = asdict(must_jump) if must_jump else None


def _resolve_reverted_allowed_moves(game: Game, last_move_entry: MoveEntry | None) -> None:
    if last_move_entry and last_move_entry.allowed_moves:
        game.allowed_moves = last_move_entry.allowed_moves
        return
    game.allowed_moves = get_all_valid_moves(
        state_from_model(game).board,
        state_from_model(game).current_player.move_dir,
        state_from_model(game).must_jump_piece,
    )


def _refresh_winner(game: Game) -> None:
    state = state_from_model(game)
    game.winner_id = next((p.id for p in state.players if p.id != state.current_player_id), None) if not get_all_valid_moves(state.board, state.current_player.move_dir, state.must_jump_piece) else None


def _revert_last_move(game: Game) -> Game:
    last = MoveEntry.objects.filter(game=game).last()
    if not last:
        return game
    with transaction.atomic():
        MoveEntry.objects.filter(id__in=_get_ids_to_revert(game, last.player_dir)).delete()
        last_entry, last_move, board = _build_reverted_state_context(game)
        _apply_reverted_turn(game, last.player_dir, last_move, board)
        _resolve_reverted_allowed_moves(game, last_entry)
        _refresh_winner(game)
        game.save()
    return game


def revert_last_n_plies(game: Game, plies: int) -> Game:
    current_game = game
    for _ in range(plies):
        before = MoveEntry.objects.filter(game=current_game).count()
        current_game = _revert_last_move(current_game)
        after = MoveEntry.objects.filter(game=current_game).count()
        if after >= before:
            break
    return current_game