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
    from anthropic import APIConnectionError, APITimeoutError, Anthropic, RateLimitError
except Exception:
    APIConnectionError = APITimeoutError = RateLimitError = Exception
    Anthropic = None


class AnthropicOpponent(BaseOpponent):
    def __init__(self, model: str, api_key: str, timeout_seconds: float = 20.0) -> None:
        if Anthropic is None:
            raise AIConfigurationError('anthropic package is not installed.')
        if not api_key.strip():
            raise AIConfigurationError('ANTHROPIC_API_KEY is required for Anthropic provider.')

        self.model = model
        self._client = Anthropic(api_key=api_key.strip(), timeout=timeout_seconds)

    def pick_move(self, board_state: List[List[int]], allowed_moves: List[dict]) -> MoveResponse:
        prompt = json.dumps({'board_state': board_state, 'allowed_moves': allowed_moves}, ensure_ascii=True)

        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=256,
                temperature=0,
                system=(
                    'Return only JSON: {"from_pos":{"row":int,"col":int},'
                    '"to_pos":{"row":int,"col":int}} chosen from allowed_moves.'
                ),
                messages=[{'role': 'user', 'content': prompt}],
            )
        except (RateLimitError, APITimeoutError, APIConnectionError) as error:
            raise AITimeoutError(f'Anthropic request failed: {error}') from error

        try:
            raw_text = ''.join(
                part.text for part in message.content
                if getattr(part, 'type', None) == 'text' and getattr(part, 'text', None)
            )
            payload = json.loads(raw_text)
            move = MoveResponse.model_validate(payload)
        except (json.JSONDecodeError, ValidationError, TypeError) as error:
            raise AIHallucinationError('Anthropic returned invalid JSON move payload.') from error

        if not is_allowed_move(move, allowed_moves):
            raise AIHallucinationError('Anthropic returned move not present in allowed_moves.')

        return move
