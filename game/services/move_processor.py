from dataclasses import asdict
from typing import Optional

from django.db import transaction
from django.shortcuts import get_object_or_404

from game.exceptions import InvalidMoveError
from game.models import Game, MoveEntry
from .entities import GameState, Move, Player, Position, Checker
from .game_logic import apply_move, check_promotion
from .game_queries import state_from_model
from .move_calculator import get_all_valid_moves


def _calculate_allowed_moves(state: GameState) -> list[dict]:
    return get_all_valid_moves(
        state.board,
        state.current_player.move_dir,
        state.must_jump_piece,
    )


def _winner_id_from_allowed_moves(state: GameState, allowed_moves: list[dict]) -> int | None:
    if allowed_moves:
        return None
    return next((p.id for p in state.players if p.id != state.current_player_id), None)


def _default_ai_player_id(players: list[Player]) -> int:
    return players[1].id


def create_new_game() -> Game:
    from .game_utils import create_initial_game_state

    state = create_initial_game_state()
    state_dict = asdict(state)
    allowed_moves = _calculate_allowed_moves(state)
    ai_id = _default_ai_player_id(state.players)

    game_model = Game.objects.create(
        board=state_dict['board'],
        players=state_dict['players'],
        current_player_id=state_dict['current_player_id'],
        must_jump_piece=state_dict['must_jump_piece'],
        allowed_moves=allowed_moves,
        ai_player_id=ai_id,
        winner_id=_winner_id_from_allowed_moves(state, allowed_moves),
    )

    return game_model


def _update_game_model(model: Game, state: GameState, allowed_moves: list[dict]) -> None:
    data = asdict(state)
    model.board = data['board']
    model.current_player_id = data['current_player_id']
    model.must_jump_piece = data['must_jump_piece']
    model.allowed_moves = allowed_moves
    model.winner_id = _winner_id_from_allowed_moves(state, allowed_moves)
    model.save()


def _piece_for_promotion_check(state: GameState, from_pos: Position) -> Checker:
    piece = state.board[from_pos.row][from_pos.col]
    if not piece:
        raise InvalidMoveError("This move violates the rules of checkers.")
    return piece


def _record_move(
    model: Game,
    cur_state: GameState,
    from_pos: Position,
    target: Move,
    next_allowed_moves: list[dict],
) -> None:
    piece = _piece_for_promotion_check(cur_state, from_pos)
    is_promoted = check_promotion(piece, target.row)
    MoveEntry.objects.create(
        game=model,
        player_dir=cur_state.current_player.move_dir,
        from_pos=asdict(from_pos),
        to_pos={'row': target.row, 'col': target.col},
        is_jump=target.type == 'jump',
        is_promoted=is_promoted,
        allowed_moves=next_allowed_moves,
    )


def _target_from_cached_moves(
    cached_moves: list[dict],
    from_pos: Position,
    to_dict: dict,
) -> Optional[Move]:
    for piece_entry in cached_moves:
        source = piece_entry.get('from_pos')
        if not source:
            continue
        if source.get('row') != from_pos.row or source.get('col') != from_pos.col:
            continue

        for move in piece_entry.get('moves', []):
            if move.get('row') == to_dict['row'] and move.get('col') == to_dict['col']:
                captured = move.get('captured')
                return Move(
                    row=move['row'],
                    col=move['col'],
                    type=move['type'],
                    captured=Position(**captured) if captured else None,
                )
    return None


def _get_or_build_cached_moves(model: Game, state: GameState) -> list[dict]:
    if model.allowed_moves:
        return model.allowed_moves
    recalculated_moves = _calculate_allowed_moves(state)
    Game.objects.filter(id=model.id).update(allowed_moves=recalculated_moves)
    model.allowed_moves = recalculated_moves
    return recalculated_moves


def ensure_allowed_moves(game: Game) -> list[dict]:
    return _get_or_build_cached_moves(game, state_from_model(game))


def is_ai_turn(game: Game) -> bool:
    return (
        game.ai_player_id is not None
        and game.current_player_id == game.ai_player_id
        and game.winner_id is None
    )


def count_total_allowed_moves(allowed_moves: list[dict]) -> int:
    return sum(len(piece_entry.get('moves', [])) for piece_entry in allowed_moves)


def extract_single_allowed_move(allowed_moves: list[dict]) -> tuple[dict, dict] | None:
    for piece_entry in allowed_moves:
        from_pos = piece_entry.get('from_pos')
        if not from_pos:
            continue
        for move in piece_entry.get('moves', []):
            return (
                {'row': from_pos['row'], 'col': from_pos['col']},
                {'row': move['row'], 'col': move['col']},
            )
    return None


def _position_from_dict(data: dict) -> Position:
    return Position(row=data['row'], col=data['col'])


def process_move_request(game_id: str, from_dict: dict, to_dict: dict) -> Game:
    game_model = get_object_or_404(Game, id=game_id)

    if game_model.winner_id:
        raise InvalidMoveError("This game is already over.")

    current_state = state_from_model(game_model)
    from_pos = _position_from_dict(from_dict)
    cached_moves = _get_or_build_cached_moves(game_model, current_state)
    target = _target_from_cached_moves(cached_moves, from_pos, to_dict)

    if not target:
        raise InvalidMoveError("This move violates the rules of checkers.")

    upd = apply_move(current_state, from_pos, target)
    next_allowed_moves = _calculate_allowed_moves(upd)

    with transaction.atomic():
        _update_game_model(game_model, upd, next_allowed_moves)
        _record_move(game_model, current_state, from_pos, target, next_allowed_moves)
    return game_model