"""LLM Provider base interface, models, and exceptions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""

    DEEPSEEK = "deepseek"
    GEMINI = "gemini"


# =============================================================================
# Exceptions
# =============================================================================


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, provider: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(f"[{provider}] {message}")


class LLMRateLimitError(LLMProviderError):
    """Raised when provider rate limit is exceeded."""

    def __init__(
        self,
        provider: str,
        retry_after: float | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded. Retry after {retry_after}s" if retry_after else "Rate limit exceeded",
            provider,
            details,
        )


class LLMAuthError(LLMProviderError):
    """Raised when provider authentication fails."""

    def __init__(self, provider: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("Authentication failed - check API key", provider, details)


class LLMConnectionError(LLMProviderError):
    """Raised when connection to provider fails."""

    def __init__(self, provider: str, details: dict[str, Any] | None = None) -> None:
        super().__init__("Connection to provider failed", provider, details)


class LLMModelNotFoundError(LLMProviderError):
    """Raised when requested model is not available."""

    def __init__(self, provider: str, model: str, details: dict[str, Any] | None = None) -> None:
        self.model = model
        super().__init__(f"Model '{model}' not found or not available", provider, details)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class LLMMessage:
    """A single message in a conversation."""

    role: str  # "system", "user", "assistant"
    content: str
    images: list[bytes] | None = None  # For vision requests (base64 or raw bytes)

    def __post_init__(self) -> None:
        if self.role not in ("system", "user", "assistant"):
            raise ValueError(f"Invalid role: {self.role}. Must be 'system', 'user', or 'assistant'")


@dataclass
class LLMRequest:
    """Request to an LLM provider."""

    messages: list[LLMMessage]
    model: str | None = None  # If None, use provider default
    max_tokens: int | None = None
    temperature: float = 0.7
    top_p: float | None = None
    stop: list[str] | None = None

    @classmethod
    def from_prompt(cls, prompt: str, system_prompt: str | None = None, **kwargs: Any) -> LLMRequest:
        """Create a request from a simple prompt string."""
        messages = []
        if system_prompt:
            messages.append(LLMMessage(role="system", content=system_prompt))
        messages.append(LLMMessage(role="user", content=prompt))
        return cls(messages=messages, **kwargs)


@dataclass
class LLMUsage:
    """Token usage and cost tracking."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int = field(init=False)
    estimated_cost_usd: float | None = None

    def __post_init__(self) -> None:
        self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    content: str
    usage: LLMUsage
    model: str
    provider: str
    finish_reason: str | None = None
    raw_response: dict[str, Any] | None = None


# =============================================================================
# Provider Protocol
# =============================================================================


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    provider_name: str

    @abstractmethod
    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a completion for the given request.

        Args:
            request: The LLM request containing messages and parameters.

        Returns:
            LLMResponse with the generated content and usage stats.

        Raises:
            LLMProviderError: If the request fails.
            LLMRateLimitError: If rate limit is exceeded.
            LLMAuthError: If authentication fails.
        """
        ...

    @abstractmethod
    async def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        """
        Convenience method for chat completions.

        Args:
            messages: List of messages in the conversation.
            **kwargs: Additional parameters (model, max_tokens, temperature, etc.)

        Returns:
            LLMResponse with the generated content and usage stats.
        """
        ...

    @abstractmethod
    async def complete_with_vision(
        self, prompt: str, images: list[bytes], **kwargs: Any
    ) -> LLMResponse:
        """
        Generate a completion that includes image analysis.

        Args:
            prompt: Text prompt describing what to do with the images.
            images: List of images as bytes (JPEG, PNG, etc.)
            **kwargs: Additional parameters.

        Returns:
            LLMResponse with the generated content and usage stats.

        Raises:
            NotImplementedError: If provider doesn't support vision.
        """
        ...

    @abstractmethod
    def estimate_cost(self, usage: LLMUsage, model: str) -> float:
        """
        Estimate the cost for the given usage.

        Args:
            usage: Token usage information.
            model: The model used.

        Returns:
            Estimated cost in USD.
        """
        ...

    async def health_check(self) -> bool:
        """
        Check if the provider is available and configured correctly.

        Returns:
            True if provider is healthy, False otherwise.
        """
        try:
            # Simple test request
            response = await self.complete(
                LLMRequest.from_prompt("Say 'ok'", max_tokens=5)
            )
            return bool(response.content)
        except Exception:
            return False
