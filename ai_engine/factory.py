from __future__ import annotations

import os

from ai_engine.base import BaseOpponent
from ai_engine.exceptions import AIConfigurationError
from ai_engine.providers.anthropic import AnthropicOpponent
from ai_engine.providers.openai import OpenAIOpponent
from ai_engine.providers.groq import QwenOpponent
from ai_engine.providers.random import RandomOpponent


class OpponentFactory:
    DEFAULT_OPENAI_MODEL = 'gpt-4o'
    DEFAULT_ANTHROPIC_MODEL = 'claude-3-5-sonnet-latest'
    DEFAULT_QWEN_MODEL = 'llama-3.1-8b-instant'

    @classmethod
    def create(cls, provider_spec: str | None = None) -> BaseOpponent:
        raw_spec = (provider_spec or os.getenv('AI_PROVIDER_STR') or 'random').strip()
        provider_name, _, model_name = raw_spec.partition(':')
        provider = provider_name.strip().lower()
        model = model_name.strip()

        if provider == 'openai':
            return OpenAIOpponent(
                model=model or cls.DEFAULT_OPENAI_MODEL,
                api_key=os.getenv('OPENAI_API_KEY', ''),
            )
        if provider == 'anthropic':
            return AnthropicOpponent(
                model=model or cls.DEFAULT_ANTHROPIC_MODEL,
                api_key=os.getenv('ANTHROPIC_API_KEY', ''),
            )
        if provider == 'groq':
            return QwenOpponent(
                model=model or cls.DEFAULT_QWEN_MODEL,
                api_key=os.getenv('GROQ_API_KEY', ''),
            )
        if provider == 'random':
            return RandomOpponent()

        raise AIConfigurationError(f'Unsupported AI provider: {raw_spec}. Valid providers: openai, anthropic, grok, qwen, random')
