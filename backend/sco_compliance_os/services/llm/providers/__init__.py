"""Provider concreti per il router multi-LLM.

Ogni provider implementa LLMProvider Protocol e normalizza eventi a ChunkEvent.
"""

from __future__ import annotations

from sco_compliance_os.services.llm.providers.anthropic import AnthropicProvider
from sco_compliance_os.services.llm.providers.gemini import GeminiProvider
from sco_compliance_os.services.llm.providers.ollama import OllamaProvider
from sco_compliance_os.services.llm.providers.openai import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "GeminiProvider",
    "OllamaProvider",
    "OpenAIProvider",
]
