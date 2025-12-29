"""Google Gemini LLM provider implementation with vision support."""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from app.services.llm.base import (
    LLMAuthError,
    LLMConnectionError,
    LLMMessage,
    LLMModelNotFoundError,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMRequest,
    LLMResponse,
    LLMUsage,
)

logger = logging.getLogger(__name__)


# Gemini pricing per 1M tokens (as of late 2024)
GEMINI_PRICING = {
    "gemini-pro": {"input": 0.50, "output": 1.50},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},  # Free during preview
}


class GeminiProvider(LLMProvider):
    """Google Gemini LLM provider with vision support."""

    provider_name = "gemini"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
    DEFAULT_MODEL = "gemini-1.5-flash"
    DEFAULT_VISION_MODEL = "gemini-1.5-flash"

    def __init__(
        self,
        api_key: str,
        default_model: str | None = None,
        vision_model: str | None = None,
        timeout: float = 60.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Gemini provider.

        Args:
            api_key: Google AI API key.
            default_model: Default model for text requests.
            vision_model: Model to use for vision requests.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for transient errors.
        """
        self.api_key = api_key
        self.default_model = default_model or self.DEFAULT_MODEL
        self.vision_model = vision_model or self.DEFAULT_VISION_MODEL
        self.timeout = timeout
        self.max_retries = max_retries

    def _convert_messages_to_contents(
        self, messages: list[LLMMessage]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        Convert LLMMessage objects to Gemini contents format.

        Returns:
            Tuple of (contents list, system instruction).
        """
        contents = []
        system_instruction = None

        for msg in messages:
            if msg.role == "system":
                # Gemini handles system prompts separately
                system_instruction = msg.content
            else:
                role = "user" if msg.role == "user" else "model"
                parts: list[dict[str, Any]] = [{"text": msg.content}]

                # Add images if present
                if msg.images:
                    for image_bytes in msg.images:
                        # Detect image type from magic bytes
                        mime_type = self._detect_image_type(image_bytes)
                        parts.append({
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.standard_b64encode(image_bytes).decode("utf-8"),
                            }
                        })

                contents.append({"role": role, "parts": parts})

        return contents, system_instruction

    def _detect_image_type(self, image_bytes: bytes) -> str:
        """Detect image MIME type from magic bytes."""
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if image_bytes[:2] == b"\xff\xd8":
            return "image/jpeg"
        if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            return "image/webp"
        # Default to JPEG
        return "image/jpeg"

    async def _make_request(
        self,
        model: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Make an API request to Gemini.

        Args:
            model: Model name to use.
            payload: Request payload.

        Returns:
            API response as dictionary.

        Raises:
            LLMProviderError: If request fails.
        """
        url = f"{self.BASE_URL}/models/{model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 401 or response.status_code == 403:
                    raise LLMAuthError(
                        provider=self.provider_name,
                        details={"status_code": response.status_code, "response": response.text},
                    )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise LLMRateLimitError(
                        provider=self.provider_name,
                        retry_after=float(retry_after) if retry_after else None,
                        details={"response": response.text},
                    )

                if response.status_code == 404:
                    raise LLMModelNotFoundError(
                        provider=self.provider_name,
                        model=model,
                        details={"response": response.text},
                    )

                if response.status_code >= 400:
                    raise LLMProviderError(
                        message=f"API error: {response.status_code}",
                        provider=self.provider_name,
                        details={"status_code": response.status_code, "response": response.text},
                    )

                return response.json()

            except httpx.ConnectError as e:
                raise LLMConnectionError(
                    provider=self.provider_name,
                    details={"error": str(e)},
                ) from e
            except httpx.TimeoutException as e:
                raise LLMConnectionError(
                    provider=self.provider_name,
                    details={"error": f"Request timeout: {e}"},
                ) from e

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a completion for the given request.

        Args:
            request: The LLM request containing messages and parameters.

        Returns:
            LLMResponse with the generated content and usage stats.
        """
        # Check if any message has images - use vision model if so
        has_images = any(msg.images for msg in request.messages)
        model = request.model or (self.vision_model if has_images else self.default_model)

        contents, system_instruction = self._convert_messages_to_contents(request.messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
            },
        }

        if request.max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = request.max_tokens
        if request.top_p is not None:
            payload["generationConfig"]["topP"] = request.top_p
        if request.stop:
            payload["generationConfig"]["stopSequences"] = request.stop
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        logger.debug(f"[Gemini] Sending request to model {model}")

        response_data = await self._make_request(model, payload)

        # Parse response
        candidates = response_data.get("candidates", [])
        if not candidates:
            raise LLMProviderError(
                message="No response candidates returned",
                provider=self.provider_name,
                details={"response": response_data},
            )

        candidate = candidates[0]
        content_parts = candidate.get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in content_parts)
        finish_reason = candidate.get("finishReason")

        # Parse usage
        usage_metadata = response_data.get("usageMetadata", {})
        usage = LLMUsage(
            prompt_tokens=usage_metadata.get("promptTokenCount", 0),
            completion_tokens=usage_metadata.get("candidatesTokenCount", 0),
        )

        # Estimate cost
        usage.estimated_cost_usd = self.estimate_cost(usage, model)

        logger.info(
            f"[Gemini] Completed request: {usage.total_tokens} tokens, "
            f"${usage.estimated_cost_usd:.6f} estimated cost"
        )

        return LLMResponse(
            content=content,
            usage=usage,
            model=model,
            provider=self.provider_name,
            finish_reason=finish_reason,
            raw_response=response_data,
        )

    async def chat(self, messages: list[LLMMessage], **kwargs: Any) -> LLMResponse:
        """
        Convenience method for chat completions.

        Args:
            messages: List of messages in the conversation.
            **kwargs: Additional parameters (model, max_tokens, temperature, etc.)

        Returns:
            LLMResponse with the generated content and usage stats.
        """
        request = LLMRequest(
            messages=messages,
            model=kwargs.get("model"),
            max_tokens=kwargs.get("max_tokens"),
            temperature=kwargs.get("temperature", 0.7),
            top_p=kwargs.get("top_p"),
            stop=kwargs.get("stop"),
        )
        return await self.complete(request)

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
        """
        # Create a message with images attached
        message = LLMMessage(role="user", content=prompt, images=images)

        request = LLMRequest(
            messages=[message],
            model=kwargs.get("model", self.vision_model),
            max_tokens=kwargs.get("max_tokens"),
            temperature=kwargs.get("temperature", 0.7),
            top_p=kwargs.get("top_p"),
            stop=kwargs.get("stop"),
        )

        return await self.complete(request)

    def estimate_cost(self, usage: LLMUsage, model: str) -> float:
        """
        Estimate the cost for the given usage.

        Args:
            usage: Token usage information.
            model: The model used.

        Returns:
            Estimated cost in USD.
        """
        # Normalize model name (handle versioned names)
        pricing_key = model
        if model not in GEMINI_PRICING:
            # Try to match partial model names
            for key in GEMINI_PRICING:
                if key in model or model in key:
                    pricing_key = key
                    break
            else:
                pricing_key = "gemini-1.5-flash"  # Default pricing

        pricing = GEMINI_PRICING[pricing_key]
        input_cost = (usage.prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (usage.completion_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
