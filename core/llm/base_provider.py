"""
Base LLM Provider Interface

Abstract base class that all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Standard LLM response format"""
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    cached: bool = False
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers (OpenAI, Gemini, Ollama) must implement these methods.
    """

    def __init__(self, model: str, **kwargs):
        """
        Initialize the provider.

        Args:
            model: Model name/identifier
            **kwargs: Provider-specific configuration
        """
        self.model = model
        self.config = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate completion from messages.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Returns:
            LLMResponse object
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream completion from messages.

        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Provider-specific parameters

        Yields:
            Chunks of generated text
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if provider is available and configured.

        Returns:
            True if provider can be used
        """
        pass

    @abstractmethod
    def get_cost_estimate(self, tokens: int) -> float:
        """
        Estimate cost for given token count.

        Args:
            tokens: Number of tokens

        Returns:
            Estimated cost in USD
        """
        pass

    def get_name(self) -> str:
        """Get provider name"""
        return self.__class__.__name__.replace("Provider", "")

    def supports_streaming(self) -> bool:
        """Check if provider supports streaming"""
        return True

    def supports_vision(self) -> bool:
        """Check if provider supports vision/images"""
        return False
