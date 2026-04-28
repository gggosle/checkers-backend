from __future__ import annotations

import json
from typing import List

from groq import Groq
from pydantic import ValidationError


from ai_engine.base import BaseOpponent, MoveResponse, is_allowed_move
from ai_engine.exceptions import AIConfigurationError, AIHallucinationError, AITimeoutError


class QwenOpponent(BaseOpponent):
    def __init__(self, model: str, api_key: str, timeout_seconds: float = 20.0) -> None:
        if not api_key.strip():
            raise AIConfigurationError('GROQ_API_KEY is required for Qwen provider.')

        self.model = model
        self._client = Groq(
            api_key=api_key.strip(),
            timeout=timeout_seconds,
        )

    def pick_move(self, board_state: List[List[int]], allowed_moves: List[dict]) -> MoveResponse:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {
                        'role': 'system',
                        'content': (
                            'You are a checkers AI. Return ONLY valid JSON with '
                            'keys "from_pos" {row, col} and "to_pos" {row, col}. '
                            "DO NOT provide multiple options. DO NOT provide explanations or commentary. "
                            "Output exactly one JSON block and nothing else.\n"
                            "Format: {\"from_pos\": {\"row\": 0, \"col\": 0}, \"to_pos\": {\"row\": 0, \"col\": 0}}"
                            'Choose the best move strictly from allowed_moves. No markdown, no explanation.'
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
        except Exception as error:
            raise AITimeoutError(f'Groq request failed: {error}') from error

        try:
            content = response.choices[0].message.content
            if not content:
                raise AIHallucinationError(f'Groq empty (finish_reason={response.choices[0].finish_reason}).')
            content = str(content).strip()
            if not content:
                raise AIHallucinationError(f'Groq blank after strip (finish_reason={response.choices[0].finish_reason}).')
            if content.startswith('```'):
                lines = content.split('\n')
                content = '\n'.join(lines[1:-1] if lines[-1].strip() == '```' else lines[1:])
            payload = json.loads(content)
            move = MoveResponse.model_validate(payload)
        except (IndexError, json.JSONDecodeError, ValidationError) as error:
            raise AIHallucinationError(f'Groq parse error: {repr(content[:300])}') from error

        if not is_allowed_move(move, allowed_moves):
            raise AIHallucinationError(f'Groq returned move not in allowed_moves: {move.model_dump()}')

        return move