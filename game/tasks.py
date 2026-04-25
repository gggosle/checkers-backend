from __future__ import annotations

from django.db import transaction

from ai_engine.factory import OpponentFactory
from game.models import Game
from game.services import orchestrator

try:
    from django_rq import job
except Exception:
    def job(*_args, **_kwargs):
        def decorator(func):
            return func
        return decorator


def _board_to_int_matrix(board: list[list[dict | None]]) -> list[list[int]]:
    matrix: list[list[int]] = []
    for row in board:
        encoded_row: list[int] = []
        for cell in row:
            if not cell:
                encoded_row.append(0)
                continue
            direction = int(cell.get('direction', 0))
            if cell.get('is_king'):
                encoded_row.append(2 if direction > 0 else -2)
            else:
                encoded_row.append(1 if direction > 0 else -1)
        matrix.append(encoded_row)
    return matrix


def _position_to_dict(position) -> dict:
    if hasattr(position, 'model_dump'):
        return position.model_dump()
    return {'row': position.row, 'col': position.col}


@job('default', timeout=60)
def run_ai_turn(game_id: str) -> dict:
    with transaction.atomic():
        game = Game.objects.select_for_update().filter(id=game_id).first()
        if not game:
            return {'status': 'skipped', 'reason': 'game_not_found'}
        if not orchestrator.is_ai_turn(game):
            return {'status': 'skipped', 'reason': 'not_ai_turn'}

        allowed_moves = orchestrator.ensure_allowed_moves(game)
        if orchestrator.count_total_allowed_moves(allowed_moves) == 0:
            return {'status': 'skipped', 'reason': 'no_legal_moves'}

        opponent = OpponentFactory.create()
        decision = opponent.pick_move(_board_to_int_matrix(game.board), allowed_moves)
        updated = orchestrator.process_move_request(
            str(game.id),
            from_dict=_position_to_dict(decision.from_pos),
            to_dict=_position_to_dict(decision.to_pos),
        )

        return {
            'status': 'completed',
            'game_id': str(updated.id),
            'current_player_id': updated.current_player_id,
            'winner_id': updated.winner_id,
        }
