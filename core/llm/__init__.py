"""
LLM Abstraction Layer (Phase 5)

Unified interface for multiple LLM providers:
- OpenAI (GPT-4o-mini, GPT-4, etc.)
- Google Gemini (gemini-2.5-flash, gemini-pro)
- Ollama (Local LLMs: Llama 3, Mistral, Phi-3, etc.)

Benefits:
- Provider-agnostic code
- Easy switching between providers
- Local LLM support (zero cost)
- Consistent API across providers
- Built-in caching and error handling
"""

from core.llm.llm_manager import LLMManager, get_llm_manager
from core.llm.providers.openai_provider import OpenAIProvider
from core.llm.providers.gemini_provider import GeminiProvider
from core.llm.providers.ollama_provider import OllamaProvider

__all__ = [
    'LLMManager',
    'get_llm_manager',
    'OpenAIProvider',
    'GeminiProvider',
    'OllamaProvider',
]
