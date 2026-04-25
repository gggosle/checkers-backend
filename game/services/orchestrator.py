from dataclasses import asdict
from typing import Optional

from django.db import transaction
from django.shortcuts import get_object_or_404

from game.exceptions import InvalidMoveError
from game.models import Game, MoveEntry

from .board_utils import reconstruct_board
from .constants import GameConfig, GameRules
from .entities import Board, Checker, GameState, Move, MoveRecord, Player, Position
from .game_rules import apply_move, check_promotion, get_all_valid_moves, has_jump_available
from .game_utils import create_initial_game_state


def _position_from_dict(data: dict) -> Position:
    return Position(row=data['row'], col=data['col'])


def _checker_board_from_json(board_json: list[list[dict | None]]) -> Board:
    return [[Checker(**cell) if cell else None for cell in row] for row in board_json]


def _move_record_from_entry(entry: MoveEntry) -> MoveRecord:
    return MoveRecord(
        player_id=entry.player_dir,
        from_pos=_position_from_dict(entry.from_pos),
        to_pos=_position_from_dict(entry.to_pos),
        is_jump=entry.is_jump,
        promoted_to_king=entry.is_promoted,
    )


def _board_to_json(board: Board) -> list[list[dict | None]]:
    return [[asdict(cell) if cell else None for cell in row] for row in board]


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


def _to_state(model: Game) -> GameState:
    return GameState(
        board=_checker_board_from_json(model.board),
        players=[Player(**p) for p in model.players],
        current_player_id=model.current_player_id,
        must_jump_piece=Position(**model.must_jump_piece) if model.must_jump_piece else None,
    )

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
    return _get_or_build_cached_moves(game, _to_state(game))


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


def process_move_request(game_id: str, from_dict: dict, to_dict: dict) -> Game:
    game_model = get_object_or_404(Game, id=game_id)

    if game_model.winner_id:
        raise InvalidMoveError("This game is already over.")

    current_state = _to_state(game_model)
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


def _get_ids_to_revert(game: Game, player_dir: int) -> list:
    ids = []
    for move in MoveEntry.objects.filter(game=game).order_by('-created_at'):
        if move.player_dir != player_dir:
            break
        ids.append(move.id)
    return ids


def _calculate_must_jump_piece(last_move: MoveRecord | None, board: Board):
    if last_move and last_move.is_jump:
        if has_jump_available(board, last_move.to_pos.row, last_move.to_pos.col):
            return last_move.to_pos
    return None


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
    game.board = _board_to_json(board)
    player = next(p for p in game.players if p['move_dir'] == last_player_dir)
    game.current_player_id = player['id']
    must_jump = _calculate_must_jump_piece(last_move, board)
    game.must_jump_piece = asdict(must_jump) if must_jump else None


def _resolve_reverted_allowed_moves(game: Game, last_move_entry: MoveEntry | None) -> None:
    if last_move_entry and last_move_entry.allowed_moves:
        game.allowed_moves = last_move_entry.allowed_moves
        return
    game.allowed_moves = _calculate_allowed_moves(_to_state(game))


def _refresh_winner(game: Game) -> None:
    state = _to_state(game)
    game.winner_id = _winner_id_from_allowed_moves(state, game.allowed_moves)


def revert_last_move(game: Game) -> Game:
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
    steps = max(plies, 0)
    current_game = game
    for _ in range(steps):
        before = MoveEntry.objects.filter(game=current_game).count()
        current_game = revert_last_move(current_game)
        after = MoveEntry.objects.filter(game=current_game).count()
        if after >= before:
            break
    return current_game
