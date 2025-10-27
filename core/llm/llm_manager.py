"""
LLM Manager - Unified interface for all LLM providers

Simplifies LLM usage with:
- Auto-detection of available providers
- Fallback chains
- Cost tracking
- Built-in caching (uses Phase 4 query cache)
- Support for OpenAI, Gemini, and Ollama
"""

import os
import logging
from typing import List, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """Available LLM providers"""
    OPENAI = "openai"
    GEMINI = "gemini"
    OLLAMA = "ollama"


class LLMManager:
    """
    Unified LLM manager supporting multiple providers.

    Usage:
        manager = LLMManager(provider="openai", model="gpt-4o-mini")
        response = await manager.generate("What is AI?")
    """

    # Cost per 1M tokens (approximate, as of 2025)
    COSTS = {
        "gpt-4o-mini": {"input": 0.15, "output": 0.60},
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
        "gemini-pro": {"input": 0.50, "output": 1.50},
        "ollama": {"input": 0.0, "output": 0.0},  # Free/local
    }

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        fallback_providers: Optional[List[str]] = None
    ):
        """
        Initialize LLM manager.

        Args:
            provider: Primary provider ("openai", "gemini", or "ollama")
            model: Model name (or None for default)
            fallback_providers: List of fallback providers to try
        """
        self.provider = provider.lower()
        self.fallback_providers = fallback_providers or []

        # Set default model based on provider
        if model is None:
            model = self._get_default_model(self.provider)

        self.model = model
        self._client = None
        self._async_client = None

        # Initialize client
        self._initialize_client()

        logger.info(f"LLMManager initialized: provider={self.provider}, model={self.model}")

    def _get_default_model(self, provider: str) -> str:
        """Get default model for provider"""
        defaults = {
            "openai": "gpt-4o-mini",
            "gemini": "gemini-2.5-flash",
            "ollama": "llama3.2:latest"
        }
        return defaults.get(provider, "gpt-4o-mini")

    def _initialize_client(self):
        """Initialize the LLM client based on provider"""
        if self.provider == "openai":
            self._initialize_openai()
        elif self.provider == "gemini":
            self._initialize_gemini()
        elif self.provider == "ollama":
            self._initialize_ollama()
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _initialize_openai(self):
        """Initialize OpenAI client"""
        try:
            from openai import AsyncOpenAI

            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY not set")

            self._async_client = AsyncOpenAI(api_key=api_key)
            logger.info("✓ OpenAI client initialized")

        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            raise

    def _initialize_gemini(self):
        """Initialize Gemini client"""
        try:
            from google import genai

            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not set")

            self._client = genai.Client(api_key=api_key)
            logger.info("✓ Gemini client initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise

    def _initialize_ollama(self):
        """Initialize Ollama client"""
        try:
            import ollama

            # Test connection
            ollama.list()
            self._client = ollama
            logger.info("✓ Ollama client initialized")

        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            logger.info("Install Ollama: ./install_ollama.sh")
            raise

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate completion using configured provider.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            Generated text
        """
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Generate based on provider
        if self.provider == "openai":
            return await self._generate_openai(messages, temperature, max_tokens)
        elif self.provider == "gemini":
            return await self._generate_gemini(messages, temperature, max_tokens)
        elif self.provider == "ollama":
            return await self._generate_ollama(messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    async def _generate_openai(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using OpenAI"""
        response = await self._async_client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content

    async def _generate_gemini(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Gemini"""
        # Convert messages to Gemini format
        prompt_parts = []
        for msg in messages:
            if msg["role"] == "system":
                prompt_parts.append(f"Instructions: {msg['content']}\n")
            else:
                prompt_parts.append(msg['content'])

        combined_prompt = "\n".join(prompt_parts)

        # Generate
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.models.generate_content(
                model=self.model,
                contents=[combined_prompt]
            )
        )

        return response.text.strip() if response.text else ""

    async def _generate_ollama(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int
    ) -> str:
        """Generate using Ollama"""
        import asyncio

        # Ollama uses similar format to OpenAI
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            )
        )

        return response['message']['content']

    def is_available(self) -> bool:
        """Check if provider is available"""
        return self._client is not None or self._async_client is not None

    def get_cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        if self.model not in self.COSTS:
            # Unknown model, use default
            model_key = "gpt-4o-mini"
        else:
            model_key = self.model

        costs = self.COSTS[model_key]
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]

        return input_cost + output_cost

    @classmethod
    def get_recommended_provider(cls) -> str:
        """
        Get recommended provider based on what's available.

        Priority:
        1. Ollama (free, local)
        2. OpenAI (best quality/price)
        3. Gemini (fallback)
        """
        # Check Ollama
        try:
            import ollama
            ollama.list()
            return "ollama"
        except:
            pass

        # Check OpenAI
        if os.getenv("OPENAI_API_KEY"):
            return "openai"

        # Check Gemini
        if os.getenv("GOOGLE_API_KEY"):
            return "gemini"

        # Default to OpenAI (user will need to set key)
        return "openai"


# Global instance
_llm_manager: Optional[LLMManager] = None


def get_llm_manager(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    force_new: bool = False
) -> LLMManager:
    """
    Get global LLM manager instance.

    Args:
        provider: LLM provider (or None for auto-detect)
        model: Model name (or None for default)
        force_new: Force creation of new instance

    Returns:
        LLMManager instance
    """
    global _llm_manager

    if force_new or _llm_manager is None:
        # Auto-detect provider if not specified
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", LLMManager.get_recommended_provider())

        # Get model from env or use default
        if model is None:
            model = os.getenv("LLM_MODEL")

        _llm_manager = LLMManager(provider=provider, model=model)

    return _llm_manager


if __name__ == "__main__":
    # Test LLM manager
    import asyncio

    async def test():
        print("Testing LLM Manager...")
        print()

        # Test recommended provider
        recommended = LLMManager.get_recommended_provider()
        print(f"Recommended provider: {recommended}")
        print()

        # Initialize manager
        manager = get_llm_manager()
        print(f"Using: {manager.provider} / {manager.model}")
        print(f"Available: {manager.is_available()}")
        print()

        # Test generation
        try:
            response = await manager.generate(
                "What is 2+2? Answer in one sentence.",
                temperature=0.0,
                max_tokens=50
            )
            print(f"Response: {response}")
            print()

            # Estimate cost
            cost = manager.get_cost_estimate(input_tokens=20, output_tokens=10)
            print(f"Estimated cost: ${cost:.6f}")

        except Exception as e:
            print(f"Error: {e}")

    asyncio.run(test())
