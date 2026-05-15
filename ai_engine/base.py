from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class MovePosition(BaseModel):
    model_config = ConfigDict(extra='forbid')

    row: int = Field(ge=0, le=7)
    col: int = Field(ge=0, le=7)


class MoveResponse(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    from_pos: MovePosition = Field(validation_alias=AliasChoices('from_pos', 'fromPos'))
    to_pos: MovePosition = Field(validation_alias=AliasChoices('to_pos', 'toPos'))

class BaseOpponent(ABC):
    @abstractmethod
    def pick_move(self, board_state: List[List[int]], allowed_moves: List[dict]) -> MoveResponse:
        raise NotImplementedError


def flatten_allowed_moves(allowed_moves: List[dict]) -> List[MoveResponse]:
    flat: List[MoveResponse] = []
    for piece_entry in allowed_moves:
        from_pos = piece_entry.get('from_pos')
        if not from_pos:
            continue
        for move in piece_entry.get('moves', []):
            flat.append(
                MoveResponse.model_validate(
                    {
                        'from_pos': from_pos,
                        'to_pos': {'row': move['row'], 'col': move['col']},
                    }
                )
            )
    return flat


def is_allowed_move(move: MoveResponse, allowed_moves: List[dict]) -> bool:
    from_row = move.from_pos.row
    from_col = move.from_pos.col
    to_row = move.to_pos.row
    to_col = move.to_pos.col

    for piece_entry in allowed_moves:
        from_pos = piece_entry.get('from_pos') or {}
        if from_pos.get('row') != from_row or from_pos.get('col') != from_col:
            continue
        for allowed in piece_entry.get('moves', []):
            if allowed.get('row') == to_row and allowed.get('col') == to_col:
                return True
    return False
