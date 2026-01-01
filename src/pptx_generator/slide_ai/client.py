"""slide_ai LLM クライアントの公開エントリポイント。"""

from __future__ import annotations

from .clients import (
    AnthropicClaudeClient,
    AwsClaudeClient,
    AzureOpenAIChatClient,
    MockLLMClient,
    OpenAIChatClient,
)
from .constants import APPLICATION_JSON, DEFAULT_MAX_TOKENS
from .errors import LLMClientConfigurationError
from .factory import create_llm_client
from .models import (
    AIGenerationRequest,
    AIGenerationResponse,
    LLMClient,
    SlideMatchCandidate,
    SlideMatchRequest,
    SlideMatchResponse,
)

__all__ = [
    "AIGenerationRequest",
    "AIGenerationResponse",
    "SlideMatchCandidate",
    "SlideMatchRequest",
    "SlideMatchResponse",
    "LLMClient",
    "LLMClientConfigurationError",
    "MockLLMClient",
    "OpenAIChatClient",
    "AzureOpenAIChatClient",
    "AnthropicClaudeClient",
    "AwsClaudeClient",
    "create_llm_client",
    "APPLICATION_JSON",
    "DEFAULT_MAX_TOKENS",
]
