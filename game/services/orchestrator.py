from dataclasses import asdict
from django.shortcuts import get_object_or_404
from game.models import Game, MoveEntry
from .constants import MoveType, GameConfig, GameRules
from .game_rules import apply_move, get_valid_moves, calculate_winner, any_player_jumps_available
from .entities import GameState, Player, Position, Move, Checker
from .game_utils import create_initial_game_state

def custom_asdict(obj):
    if obj is None:
        return None
    if isinstance(obj, list):
        return [custom_asdict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: custom_asdict(v) for k, v in obj.items()}
    from enum import Enum
    if isinstance(obj, Enum):
        return obj.value
    if hasattr(obj, '__dataclass_fields__'):
        return custom_asdict(asdict(obj))
    return obj

def create_new_game() -> Game:
    state = create_initial_game_state()
    game_model = Game.objects.create(
        board=custom_asdict(state.board),
        players=custom_asdict(state.players),
        current_player=custom_asdict(state.current_player),
        must_jump_piece=custom_asdict(state.must_jump_piece) if state.must_jump_piece else None,
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

    game_model.board = custom_asdict(updated_state.board)
    game_model.current_player = custom_asdict(updated_state.current_player)
    game_model.must_jump_piece = custom_asdict(updated_state.must_jump_piece) if updated_state.must_jump_piece else None
    
    winner_player = calculate_winner(updated_state)
    if winner_player:
        game_model.winner = winner_player.id
    
    game_model.save()

    MoveEntry.objects.create(
        game=game_model,
        player_dir=current_state.current_player.move_dir,
        from_pos=asdict(from_pos),
        to_pos={'r': target_move.row, 'c': target_move.col},
        is_jump=target_move.type == MoveType.JUMP,
        is_promoted=False
    )

    return game_model

def revert_last_move(game_id: str) -> Game:
    game_model = get_object_or_404(Game, id=game_id)
    last_move = game_model.moves.last()
    
    if last_move:
        last_move.delete()
        
    all_moves = game_model.moves.all()
    initial_state = create_initial_game_state()

    from .board_utils import reconstruct_board
    from .entities import MoveEntry as EntityMoveEntry
    
    history = []
    for m in all_moves:
        history.append(EntityMoveEntry(
            id=m.id,
            player_id=0,
            from_pos=Position(row=m.from_pos['row'], col=m.from_pos['col']),
            to_pos=Position(row=m.to_pos['r'], col=m.to_pos['c']),
            is_jump=m.is_jump,
            promoted_to_king=m.is_promoted
        ))
        
    new_board = reconstruct_board(
        history, 
        GameConfig.BOARD_SIZE, 
        GameRules.PIECE_ROWS_COUNT, 
        GameRules.MOVE_DIR_UP, 
        GameRules.MOVE_DIR_DOWN
    )

    current_state = initial_state
    for m in all_moves:
        from_pos = Position(row=m.from_pos['row'], col=m.from_pos['col'])
        jumps_available = any_player_jumps_available(current_state.board, current_state.current_player.move_dir)
        valid_moves = get_valid_moves(
            current_state.board,
            current_state.current_player.move_dir,
            current_state.must_jump_piece,
            jumps_available,
            from_pos.row,
            from_pos.col
        )
        target_move = next((mv for mv in valid_moves if mv.row == m.to_pos['r'] and mv.col == m.to_pos['c']), None)
        if target_move:
            current_state = apply_move(current_state, from_pos, target_move)

    game_model.board = custom_asdict(current_state.board)
    game_model.current_player = custom_asdict(current_state.current_player)
    game_model.must_jump_piece = custom_asdict(current_state.must_jump_piece) if current_state.must_jump_piece else None
    game_model.winner = None
    game_model.save()
    
    return game_model