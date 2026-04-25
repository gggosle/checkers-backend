from __future__ import annotations

import json
from typing import List

try:
    from pydantic import ValidationError
except Exception:
    ValidationError = ValueError

from ai_engine.base import BaseOpponent, MoveResponse, is_allowed_move
from ai_engine.exceptions import AIConfigurationError, AIHallucinationError, AITimeoutError

try:
    from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
except Exception:
    APIConnectionError = APITimeoutError = RateLimitError = Exception
    OpenAI = None


class OpenAIOpponent(BaseOpponent):
    def __init__(self, model: str, api_key: str, timeout_seconds: float = 20.0) -> None:
        if OpenAI is None:
            raise AIConfigurationError('openai package is not installed.')
        if not api_key.strip():
            raise AIConfigurationError('OPENAI_API_KEY is required for OpenAI provider.')

        self.model = model
        self._client = OpenAI(api_key=api_key.strip(), timeout=timeout_seconds)

    def pick_move(self, board_state: List[List[int]], allowed_moves: List[dict]) -> MoveResponse:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={'type': 'json_object'},
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are a checkers AI. Return ONLY one JSON object with '
                            'keys from_pos {row,col} and to_pos {row,col}. '
                            'Choose strictly from allowed_moves.'
                        ),
                    },
                    {
                        'role': 'user',
                        'content': json.dumps(
                            {
                                'board_state': board_state,
                                'allowed_moves': allowed_moves,
                            },
                            ensure_ascii=True,
                            separators=(',', ':'),
                        ),
                    },
                ],
            )
        except (RateLimitError, APITimeoutError, APIConnectionError) as error:
            raise AITimeoutError(f'OpenAI request failed: {error}') from error

        try:
            content = response.choices[0].message.content or ''
            payload = json.loads(content)
            move = MoveResponse.model_validate(payload)
        except (IndexError, json.JSONDecodeError, ValidationError) as error:
            raise AIHallucinationError('OpenAI returned invalid JSON move payload.') from error

        if not is_allowed_move(move, allowed_moves):
            raise AIHallucinationError('OpenAI returned move not present in allowed_moves.')

        return move
