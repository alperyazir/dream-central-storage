"""Edge TTS provider implementation."""

from __future__ import annotations

import asyncio
import io
import logging
from typing import Any

from app.services.tts.base import (
    TTSBatchItem,
    TTSBatchResult,
    TTSConnectionError,
    TTSProvider,
    TTSProviderError,
    TTSRateLimitError,
    TTSRequest,
    TTSResponse,
)

logger = logging.getLogger(__name__)


class EdgeTTSProvider(TTSProvider):
    """Edge TTS provider using Microsoft Edge's TTS service (free, no API key required)."""

    provider_name = "edge"

    def __init__(
        self,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Edge TTS provider.

        Args:
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for transient errors.
        """
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_rate_string(self, speed: float) -> str:
        """
        Convert speed multiplier to Edge TTS rate string.

        Args:
            speed: Speed multiplier (0.5 to 2.0)

        Returns:
            Rate string (e.g., "+50%", "-25%")
        """
        # Convert multiplier to percentage change
        # 1.0 = 0%, 1.5 = +50%, 0.5 = -50%
        percentage = int((speed - 1.0) * 100)
        if percentage >= 0:
            return f"+{percentage}%"
        return f"{percentage}%"

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """
        Synthesize speech from text using Edge TTS.

        Args:
            request: The TTS request containing text and parameters.

        Returns:
            TTSResponse with the audio data and metadata.

        Raises:
            TTSProviderError: If the request fails.
            TTSConnectionError: If connection fails.
        """
        try:
            import edge_tts
        except ImportError as e:
            raise TTSProviderError(
                message="edge-tts package not installed. Run: pip install edge-tts",
                provider=self.provider_name,
                details={"error": str(e)},
            ) from e

        voice = self.get_voice(request.language, request.voice)
        rate = self._get_rate_string(request.speed)

        logger.debug(
            f"[EdgeTTS] Synthesizing {len(request.text)} chars with voice {voice}, rate {rate}"
        )

        try:
            # Create communicate instance
            communicate = edge_tts.Communicate(
                text=request.text,
                voice=voice,
                rate=rate,
            )

            # Collect audio data
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])

            audio_data = audio_buffer.getvalue()

            if not audio_data:
                raise TTSProviderError(
                    message="No audio data received from Edge TTS",
                    provider=self.provider_name,
                )

            logger.info(
                f"[EdgeTTS] Synthesized {len(request.text)} chars, "
                f"audio size: {len(audio_data)} bytes"
            )

            return TTSResponse(
                audio_data=audio_data,
                voice_used=voice,
                provider=self.provider_name,
                character_count=len(request.text),
            )

        except asyncio.TimeoutError as e:
            raise TTSConnectionError(
                provider=self.provider_name,
                details={"error": f"Request timeout: {e}"},
            ) from e
        except Exception as e:
            error_str = str(e).lower()
            if "rate limit" in error_str or "too many requests" in error_str:
                raise TTSRateLimitError(
                    provider=self.provider_name,
                    details={"error": str(e)},
                )
            if "connection" in error_str or "network" in error_str:
                raise TTSConnectionError(
                    provider=self.provider_name,
                    details={"error": str(e)},
                )
            raise TTSProviderError(
                message=f"Edge TTS synthesis failed: {e}",
                provider=self.provider_name,
                details={"error": str(e)},
            ) from e

    async def synthesize_batch(
        self, items: list[TTSBatchItem], concurrency: int = 5
    ) -> TTSBatchResult:
        """
        Synthesize speech for multiple items concurrently.

        Args:
            items: List of batch items to synthesize.
            concurrency: Maximum concurrent requests.

        Returns:
            TTSBatchResult with results and errors.
        """
        results: list[TTSResponse | None] = [None] * len(items)
        errors: list[tuple[int, str]] = []
        semaphore = asyncio.Semaphore(concurrency)

        async def process_item(index: int, item: TTSBatchItem) -> None:
            async with semaphore:
                try:
                    request = TTSRequest(
                        text=item.text,
                        voice=item.voice,
                        language=item.language,
                    )
                    response = await self.synthesize(request)
                    results[index] = response
                except Exception as e:
                    errors.append((index, str(e)))
                    logger.warning(f"[EdgeTTS] Batch item {index} failed: {e}")

        # Process all items concurrently with semaphore limiting
        tasks = [process_item(i, item) for i, item in enumerate(items)]
        await asyncio.gather(*tasks)

        success_count = sum(1 for r in results if r is not None)
        failure_count = len(errors)

        logger.info(
            f"[EdgeTTS] Batch complete: {success_count} succeeded, {failure_count} failed"
        )

        return TTSBatchResult(
            results=results,
            errors=errors,
            success_count=success_count,
            failure_count=failure_count,
        )
