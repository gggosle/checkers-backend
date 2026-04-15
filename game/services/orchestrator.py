from dataclasses import asdict
from django.shortcuts import get_object_or_404
from game.models import Game, MoveEntry
from .constants import GameConfig, GameRules
from .game_rules import apply_move, get_valid_moves, calculate_winner, any_player_jumps_available
from .board_utils import reconstruct_board
from .entities import GameState, Player, Position, Checker, MoveEntry as EntityMoveEntry
from .game_utils import create_initial_game_state

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

def process_move_request(game_id: str, from_dict: dict, to_dict: dict) -> Game:
    game_model = Game.objects.get(id=game_id)

    current_state = GameState(
        board=[[Checker(**c) if c else None for c in row] for row in game_model.board],
        players=[Player(**p) for p in game_model.players],
        current_player=Player(**game_model.current_player),
        must_jump_piece=Position(**game_model.must_jump_piece) if game_model.must_jump_piece else None,
    )

    from_pos = Position(row=from_dict['r'], col=from_dict['c'])
    
    jumps_available = any_player_jumps_available(current_state.board, current_state.current_player.move_dir)
    valid_moves = get_valid_moves(
        current_state.board,
        current_state.current_player.move_dir,
        current_state.must_jump_piece,
        jumps_available,
        from_pos.row,
        from_pos.col
    )
    
    target_move = next((m for m in valid_moves if m.row == to_dict['r'] and m.col == to_dict['c']), None)
    if not target_move:
        return game_model

    updated_state = apply_move(current_state, from_pos, target_move)
    state_dict = asdict(updated_state)

    game_model.board = state_dict['board']
    game_model.current_player = state_dict['current_player']
    game_model.must_jump_piece = state_dict['must_jump_piece']
    
    winner_player = calculate_winner(updated_state)
    if winner_player:
        game_model.winner = winner_player.id
    
    game_model.save()

    piece = current_state.board[from_pos.row][from_pos.col]
    from .game_rules import check_promotion
    is_promoted = check_promotion(piece, target_move.row)

    MoveEntry.objects.create(
        game=game_model,
        player_dir=current_state.current_player.move_dir,
        from_pos=asdict(from_pos),
        to_pos={'row': target_move.row, 'col': target_move.col},
        is_jump=target_move.type == 'jump',
        is_promoted=is_promoted
    )

    return game_model

def revert_last_move(game_id: str) -> Game:
    game = get_object_or_404(Game, id=game_id)
    last_move = MoveEntry.objects.filter(game=game).last()
    if not last_move: return game

    player_dir = last_move.player_dir
    all_moves = MoveEntry.objects.filter(game=game).order_by('-created_at')
    
    ids_to_delete = []
    for move in all_moves:
        if move.player_dir != player_dir: break
        ids_to_delete.append(move.id)
    
    MoveEntry.objects.filter(id__in=ids_to_delete).delete()

    remaining_moves = MoveEntry.objects.filter(game=game).order_by('created_at')
    history = [EntityMoveEntry(m.id, 0, Position(**m.from_pos), Position(**m.to_pos),
                               m.is_jump, m.is_promoted) for m in remaining_moves]
    
    new_board = reconstruct_board(history, GameConfig.BOARD_SIZE, GameRules.PIECE_ROWS_COUNT,
                                  GameRules.MOVE_DIR_UP, GameRules.MOVE_DIR_DOWN)

    game.board = [[asdict(c) if c else None for c in row] for row in new_board]
    game.current_player = next(p for p in game.players if p['move_dir'] == player_dir)
    game.must_jump_piece, game.winner = None, None
    game.save()
    return game