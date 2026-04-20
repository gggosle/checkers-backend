from dataclasses import asdict
from django.db import transaction
from django.shortcuts import get_object_or_404
from game.models import Game, MoveEntry
from .constants import GameConfig, GameRules
from .game_rules import apply_move, get_valid_moves, calculate_winner, any_player_jumps_available
from .board_utils import reconstruct_board
from .entities import GameState, Player, Position, Checker, MoveEntry as EntityMoveEntry
from .game_utils import create_initial_game_state
from game.exceptions import InvalidMoveError

def create_new_game() -> Game:
    state = create_initial_game_state()
    state_dict = asdict(state)

    game_model = Game.objects.create(
        board=state_dict['board'],
        players=state_dict['players'],
        current_player=state_dict['current_player'],
        must_jump_piece=state_dict['must_jump_piece']
    )

    return game_model

def get_game(game_id: str) -> Game:
    return get_object_or_404(Game, id=game_id)

def _to_state(model):
    return GameState(
        board=[[Checker(**c) if c else None for c in row] for row in model.board],
        players=[Player(**p) for p in model.players],
        current_player_id=model.current_player_id,
        must_jump_piece=Position(**model.must_jump_piece) if model.must_jump_piece else None,
    )

def _update_game_model(model, state: GameState):
    data = asdict(state)
    model.board = data['board']
    model.current_player_id = data['current_player']
    model.must_jump_piece = data['must_jump_piece']
    winner = calculate_winner(state)
    if winner: model.winner_id = winner.id
    model.save()

def _record_move(model, cur_state: GameState, from_pos: Position, target):
    from .game_rules import check_promotion
    is_promoted = check_promotion(cur_state.board[from_pos.row][from_pos.col], target.row)
    MoveEntry.objects.create(
        game=model, 
        player_dir=cur_state.current_player.move_dir,
        from_pos=asdict(from_pos),
        to_pos={'row': target.row, 'col': target.col}, 
        is_jump=target.type == 'jump',
        is_promoted=is_promoted
    )

def process_move_request(game_id: str, from_dict: dict, to_dict: dict) -> Game:
    game_model = get_object_or_404(Game, id=game_id)

    if game_model.winner_id: raise InvalidMoveError("This game is already over.")
    current_state = _to_state(game_model)
    from_pos = Position(row=from_dict['row'], col=from_dict['col'])
    current_player = current_state.current_player
    
    jumps = any_player_jumps_available(current_state.board, current_player.move_dir)
    valid = get_valid_moves(current_state.board, current_player.move_dir, current_state.must_jump_piece, jumps, from_pos.row, from_pos.col)
    
    target = next((m for m in valid if m.row == to_dict['row'] and m.col == to_dict['col']), None)
    if not target: raise InvalidMoveError("This move violates the rules of checkers.")
    upd = apply_move(current_state, from_pos, target)

    with transaction.atomic():
        _update_game_model(game_model, upd)
        _record_move(game_model, current_state, from_pos, target)
    return game_model

def _get_ids_to_revert(game, player_dir):
    ids = []
    for m in MoveEntry.objects.filter(game=game).order_by('-created_at'):
        if m.player_dir != player_dir: break
        ids.append(m.id)
    return ids

def revert_last_move(game_id: str) -> Game:
    game = get_object_or_404(Game, id=game_id)
    last = MoveEntry.objects.filter(game=game).last()
    if not last: return game
    
    MoveEntry.objects.filter(id__in=_get_ids_to_revert(game, last.player_dir)).delete()

    moves = MoveEntry.objects.filter(game=game)
    history = [EntityMoveEntry(0, Position(**m.from_pos), Position(**m.to_pos), m.is_jump, m.is_promoted) for m in moves]
    
    board = reconstruct_board(history, GameConfig.BOARD_SIZE, GameRules.PIECE_ROWS_COUNT, GameRules.MOVE_DIR_UP, GameRules.MOVE_DIR_DOWN)
    game.board = [[asdict(c) if c else None for c in row] for row in board]
    game.current_player_id = next(p for p in game.players if p['move_dir'] == last.player_dir)
    game.must_jump_piece, game.winner_id = None, None
    game.save()
    return game