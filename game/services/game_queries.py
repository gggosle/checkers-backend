from dataclasses import asdict

from .entities import Board, Checker, GameState, Player, Position


def _position_from_dict(data: dict) -> Position:
    return Position(row=data['row'], col=data['col'])


def _board_from_json(board_json: list[list[dict | None]]) -> Board:
    return [[Checker(**cell) if cell else None for cell in row] for row in board_json]


def _board_to_json(board: Board) -> list[list[dict | None]]:
    return [[asdict(cell) if cell else None for cell in row] for row in board]


def state_from_model(model) -> GameState:
    return GameState(
        board=_board_from_json(model.board),
        players=[Player(**p) for p in model.players],
        current_player_id=model.current_player_id,
        must_jump_piece=Position(**model.must_jump_piece) if model.must_jump_piece else None,
    )