from __future__ import annotations

import random
from typing import List

from ai_engine.base import BaseOpponent, MoveResponse, flatten_allowed_moves
from ai_engine.exceptions import AIHallucinationError


class RandomOpponent(BaseOpponent):
    def pick_move(self, board_state: List[List[int]], allowed_moves: List[dict]) -> MoveResponse:
        del board_state
        candidates = flatten_allowed_moves(allowed_moves)
        if not candidates:
            raise AIHallucinationError('No legal moves available for AI turn.')
        return random.choice(candidates)
