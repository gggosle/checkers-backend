from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

try:
    from pydantic import AliasChoices, BaseModel, ConfigDict, Field
except Exception:
    AliasChoices = BaseModel = ConfigDict = Field = None


if BaseModel:
    class MovePosition(BaseModel):
        model_config = ConfigDict(extra='forbid')

        row: int = Field(ge=0, le=7)
        col: int = Field(ge=0, le=7)


    class MoveResponse(BaseModel):
        model_config = ConfigDict(extra='forbid', populate_by_name=True)

        from_pos: MovePosition = Field(validation_alias=AliasChoices('from_pos', 'fromPos'))
        to_pos: MovePosition = Field(validation_alias=AliasChoices('to_pos', 'toPos'))
else:
    @dataclass(frozen=True)
    class MovePosition:
        row: int
        col: int


    @dataclass(frozen=True)
    class MoveResponse:
        from_pos: MovePosition
        to_pos: MovePosition

        @classmethod
        def model_validate(cls, payload: dict):
            from_payload = payload.get('from_pos') or payload.get('fromPos')
            to_payload = payload.get('to_pos') or payload.get('toPos')
            if not isinstance(from_payload, dict) or not isinstance(to_payload, dict):
                raise ValueError('Invalid move payload.')
            fr = int(from_payload['row'])
            fc = int(from_payload['col'])
            tr = int(to_payload['row'])
            tc = int(to_payload['col'])
            for value in (fr, fc, tr, tc):
                if value < 0 or value > 7:
                    raise ValueError('Move payload is out of bounds.')
            return cls(
                from_pos=MovePosition(fr, fc),
                to_pos=MovePosition(tr, tc),
            )

        def model_dump(self) -> dict:
            return {
                'from_pos': {'row': self.from_pos.row, 'col': self.from_pos.col},
                'to_pos': {'row': self.to_pos.row, 'col': self.to_pos.col},
            }


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
