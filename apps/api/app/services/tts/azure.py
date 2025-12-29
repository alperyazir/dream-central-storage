"""Azure TTS provider implementation using REST API."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.services.tts.base import (
    TTSAuthError,
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


class AzureTTSProvider(TTSProvider):
    """Azure Cognitive Services TTS provider using REST API."""

    provider_name = "azure"

    def __init__(
        self,
        api_key: str,
        region: str = "eastus",
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Azure TTS provider.

        Args:
            api_key: Azure Cognitive Services API key.
            region: Azure region (e.g., "eastus", "westeurope", "turkeycentral").
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retries for transient errors.
        """
        self.api_key = api_key
        self.region = region
        self.timeout = timeout
        self.max_retries = max_retries
        self._token: str | None = None
        self._token_endpoint = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        self._tts_endpoint = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

    def _get_ssml(self, text: str, voice: str, speed: float) -> str:
        """
        Generate SSML for the TTS request.

        Args:
            text: Text to synthesize.
            voice: Voice ID.
            speed: Speech rate multiplier.

        Returns:
            SSML string.
        """
        # Convert speed to percentage (1.0 = 100%, 1.5 = 150%)
        rate_percent = int(speed * 100)

        # Escape special XML characters
        escaped_text = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

        return f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
    <voice name='{voice}'>
        <prosody rate='{rate_percent}%'>{escaped_text}</prosody>
    </voice>
</speak>"""

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        """
        Get or refresh the access token.

        Args:
            client: HTTP client to use.

        Returns:
            Access token string.

        Raises:
            TTSAuthError: If authentication fails.
        """
        try:
            response = await client.post(
                self._token_endpoint,
                headers={
                    "Ocp-Apim-Subscription-Key": self.api_key,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            if response.status_code == 401:
                raise TTSAuthError(
                    provider=self.provider_name,
                    details={"status_code": 401, "response": response.text},
                )

            if response.status_code != 200:
                raise TTSProviderError(
                    message=f"Failed to get token: {response.status_code}",
                    provider=self.provider_name,
                    details={"status_code": response.status_code, "response": response.text},
                )

            return response.text

        except httpx.RequestError as e:
            raise TTSConnectionError(
                provider=self.provider_name,
                details={"error": str(e)},
            ) from e

    async def synthesize(self, request: TTSRequest) -> TTSResponse:
        """
        Synthesize speech from text using Azure TTS.

        Args:
            request: The TTS request containing text and parameters.

        Returns:
            TTSResponse with the audio data and metadata.

        Raises:
            TTSProviderError: If the request fails.
            TTSAuthError: If authentication fails.
            TTSConnectionError: If connection fails.
        """
        voice = self.get_voice(request.language, request.voice)
        ssml = self._get_ssml(request.text, voice, request.speed)

        # Determine output format
        output_format = "audio-24khz-48kbitrate-mono-mp3"
        if request.audio_format.lower() == "wav":
            output_format = "riff-24khz-16bit-mono-pcm"

        logger.debug(
            f"[AzureTTS] Synthesizing {len(request.text)} chars with voice {voice}"
        )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Get access token
            token = await self._get_token(client)

            try:
                response = await client.post(
                    self._tts_endpoint,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": output_format,
                        "User-Agent": "DreamCentralStorage-TTS",
                    },
                    content=ssml,
                )

                if response.status_code == 401:
                    raise TTSAuthError(
                        provider=self.provider_name,
                        details={"status_code": 401},
                    )

                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    raise TTSRateLimitError(
                        provider=self.provider_name,
                        retry_after=float(retry_after) if retry_after else None,
                        details={"response": response.text},
                    )

                if response.status_code != 200:
                    raise TTSProviderError(
                        message=f"Azure TTS request failed: {response.status_code}",
                        provider=self.provider_name,
                        details={
                            "status_code": response.status_code,
                            "response": response.text,
                        },
                    )

                audio_data = response.content

                if not audio_data:
                    raise TTSProviderError(
                        message="No audio data received from Azure TTS",
                        provider=self.provider_name,
                    )

                logger.info(
                    f"[AzureTTS] Synthesized {len(request.text)} chars, "
                    f"audio size: {len(audio_data)} bytes"
                )

                return TTSResponse(
                    audio_data=audio_data,
                    voice_used=voice,
                    provider=self.provider_name,
                    character_count=len(request.text),
                )

            except httpx.TimeoutException as e:
                raise TTSConnectionError(
                    provider=self.provider_name,
                    details={"error": f"Request timeout: {e}"},
                ) from e
            except httpx.RequestError as e:
                raise TTSConnectionError(
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
                    logger.warning(f"[AzureTTS] Batch item {index} failed: {e}")

        # Process all items concurrently with semaphore limiting
        tasks = [process_item(i, item) for i, item in enumerate(items)]
        await asyncio.gather(*tasks)

        success_count = sum(1 for r in results if r is not None)
        failure_count = len(errors)

        logger.info(
            f"[AzureTTS] Batch complete: {success_count} succeeded, {failure_count} failed"
        )

        return TTSBatchResult(
            results=results,
            errors=errors,
            success_count=success_count,
            failure_count=failure_count,
        )
