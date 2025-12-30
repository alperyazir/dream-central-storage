"""Unit tests for auto-processing service and integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_processing.auto_trigger import (
    AutoProcessingService,
    get_auto_processing_service,
    trigger_auto_processing,
)
from app.services.queue.models import ProcessingJob, ProcessingJobType


# =============================================================================
# AutoProcessingService Unit Tests
# =============================================================================


class TestAutoProcessingService:
    """Test AutoProcessingService class."""

    def test_is_auto_processing_enabled_default(self) -> None:
        """Test auto-processing is enabled by default."""
        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = True

        service = AutoProcessingService(settings=mock_settings)
        assert service.is_auto_processing_enabled() is True

    def test_is_auto_processing_disabled(self) -> None:
        """Test auto-processing disabled via config."""
        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = False

        service = AutoProcessingService(settings=mock_settings)
        assert service.is_auto_processing_enabled() is False

    def test_should_skip_existing_default(self) -> None:
        """Test skip existing is enabled by default."""
        mock_settings = MagicMock()
        mock_settings.ai_auto_process_skip_existing = True

        service = AutoProcessingService(settings=mock_settings)
        assert service.should_skip_existing() is True

    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    def test_is_already_processed_true(
        self,
        mock_get_retrieval: MagicMock,
    ) -> None:
        """Test is_already_processed returns True when metadata exists."""
        mock_retrieval = MagicMock()
        mock_retrieval.get_metadata.return_value = {"processing_status": "completed"}
        mock_get_retrieval.return_value = mock_retrieval

        mock_settings = MagicMock()
        service = AutoProcessingService(settings=mock_settings)

        result = service.is_already_processed("TestPub", "123", "test-book")
        assert result is True
        mock_retrieval.get_metadata.assert_called_once_with("TestPub", "123", "test-book")

    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    def test_is_already_processed_false(
        self,
        mock_get_retrieval: MagicMock,
    ) -> None:
        """Test is_already_processed returns False when no metadata."""
        mock_retrieval = MagicMock()
        mock_retrieval.get_metadata.return_value = None
        mock_get_retrieval.return_value = mock_retrieval

        mock_settings = MagicMock()
        service = AutoProcessingService(settings=mock_settings)

        result = service.is_already_processed("TestPub", "123", "test-book")
        assert result is False

    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    def test_should_auto_process_disabled_globally(
        self,
        mock_get_retrieval: MagicMock,
    ) -> None:
        """Test should_auto_process returns False when disabled globally."""
        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = False

        service = AutoProcessingService(settings=mock_settings)
        result = service.should_auto_process("TestPub", "123", "test-book")

        assert result is False
        mock_get_retrieval.assert_not_called()

    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    def test_should_auto_process_skips_existing(
        self,
        mock_get_retrieval: MagicMock,
    ) -> None:
        """Test should_auto_process skips already processed books."""
        mock_retrieval = MagicMock()
        mock_retrieval.get_metadata.return_value = {"status": "completed"}
        mock_get_retrieval.return_value = mock_retrieval

        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = True
        mock_settings.ai_auto_process_skip_existing = True

        service = AutoProcessingService(settings=mock_settings)
        result = service.should_auto_process("TestPub", "123", "test-book")

        assert result is False

    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    def test_should_auto_process_force_overrides_skip(
        self,
        mock_get_retrieval: MagicMock,
    ) -> None:
        """Test should_auto_process with force=True ignores skip setting."""
        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = True
        mock_settings.ai_auto_process_skip_existing = True

        service = AutoProcessingService(settings=mock_settings)
        result = service.should_auto_process("TestPub", "123", "test-book", force=True)

        assert result is True
        mock_get_retrieval.assert_not_called()  # Should skip metadata check

    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    def test_should_auto_process_new_book(
        self,
        mock_get_retrieval: MagicMock,
    ) -> None:
        """Test should_auto_process returns True for new book."""
        mock_retrieval = MagicMock()
        mock_retrieval.get_metadata.return_value = None  # Not processed
        mock_get_retrieval.return_value = mock_retrieval

        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = True
        mock_settings.ai_auto_process_skip_existing = True

        service = AutoProcessingService(settings=mock_settings)
        result = service.should_auto_process("TestPub", "123", "test-book")

        assert result is True


class TestAutoProcessingServiceTrigger:
    """Test trigger_processing method."""

    @pytest.mark.asyncio
    @patch("app.services.ai_processing.auto_trigger.get_queue_service")
    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    async def test_trigger_processing_enqueues_job(
        self,
        mock_get_retrieval: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test trigger_processing enqueues job when should process."""
        mock_retrieval = MagicMock()
        mock_retrieval.get_metadata.return_value = None
        mock_get_retrieval.return_value = mock_retrieval

        mock_job = MagicMock(spec=ProcessingJob)
        mock_job.job_id = "job-123"

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.return_value = mock_job
        mock_get_queue.return_value = mock_queue

        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = True
        mock_settings.ai_auto_process_skip_existing = True

        service = AutoProcessingService(settings=mock_settings)
        result = await service.trigger_processing(
            book_id=123,
            publisher="TestPub",
            book_name="test-book",
        )

        assert result == mock_job
        mock_queue.enqueue_job.assert_called_once()
        call_kwargs = mock_queue.enqueue_job.call_args.kwargs
        assert call_kwargs["book_id"] == "123"
        assert call_kwargs["publisher_id"] == "TestPub"
        assert call_kwargs["job_type"] == ProcessingJobType.FULL
        assert call_kwargs["metadata"]["auto_triggered"] is True

    @pytest.mark.asyncio
    @patch("app.services.ai_processing.auto_trigger.get_queue_service")
    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    async def test_trigger_processing_skips_when_disabled(
        self,
        mock_get_retrieval: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test trigger_processing returns None when processing disabled."""
        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = False

        service = AutoProcessingService(settings=mock_settings)
        result = await service.trigger_processing(
            book_id=123,
            publisher="TestPub",
            book_name="test-book",
        )

        assert result is None
        mock_get_queue.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.ai_processing.auto_trigger.get_queue_service")
    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    async def test_trigger_processing_with_force(
        self,
        mock_get_retrieval: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test trigger_processing with force=True."""
        mock_job = MagicMock(spec=ProcessingJob)
        mock_job.job_id = "job-456"

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.return_value = mock_job
        mock_get_queue.return_value = mock_queue

        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = True

        service = AutoProcessingService(settings=mock_settings)
        result = await service.trigger_processing(
            book_id=456,
            publisher="TestPub",
            book_name="another-book",
            force=True,
        )

        assert result == mock_job
        call_kwargs = mock_queue.enqueue_job.call_args.kwargs
        assert call_kwargs["metadata"]["force_reprocess"] is True

    @pytest.mark.asyncio
    @patch("app.services.ai_processing.auto_trigger.get_queue_service")
    @patch("app.services.ai_processing.auto_trigger.get_ai_data_retrieval_service")
    async def test_trigger_processing_handles_queue_error(
        self,
        mock_get_retrieval: MagicMock,
        mock_get_queue: MagicMock,
    ) -> None:
        """Test trigger_processing handles queue errors gracefully."""
        mock_retrieval = MagicMock()
        mock_retrieval.get_metadata.return_value = None
        mock_get_retrieval.return_value = mock_retrieval

        mock_queue = AsyncMock()
        mock_queue.enqueue_job.side_effect = Exception("Queue connection failed")
        mock_get_queue.return_value = mock_queue

        mock_settings = MagicMock()
        mock_settings.ai_auto_process_on_upload = True
        mock_settings.ai_auto_process_skip_existing = True

        service = AutoProcessingService(settings=mock_settings)
        # Should not raise, returns None on error
        result = await service.trigger_processing(
            book_id=789,
            publisher="TestPub",
            book_name="error-book",
        )

        assert result is None


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestTriggerAutoProcessingFunction:
    """Test the trigger_auto_processing convenience function."""

    @pytest.mark.asyncio
    @patch("app.services.ai_processing.auto_trigger.get_auto_processing_service")
    async def test_trigger_auto_processing_calls_service(
        self,
        mock_get_service: MagicMock,
    ) -> None:
        """Test trigger_auto_processing uses the service."""
        mock_service = MagicMock()
        mock_service.trigger_processing = AsyncMock(return_value=None)
        mock_get_service.return_value = mock_service

        await trigger_auto_processing(
            book_id=100,
            publisher="MyPub",
            book_name="my-book",
            force=False,
        )

        mock_service.trigger_processing.assert_called_once_with(
            book_id=100,
            publisher="MyPub",
            book_name="my-book",
            force=False,
        )


# =============================================================================
# Singleton Tests
# =============================================================================


class TestGetAutoProcessingService:
    """Test get_auto_processing_service singleton."""

    def test_returns_same_instance(self) -> None:
        """Test singleton returns same instance."""
        # Reset singleton
        import app.services.ai_processing.auto_trigger as module
        module._auto_processing_service = None

        with patch("app.services.ai_processing.auto_trigger.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock()

            service1 = get_auto_processing_service()
            service2 = get_auto_processing_service()

            assert service1 is service2

        # Clean up
        module._auto_processing_service = None


# =============================================================================
# Configuration Tests
# =============================================================================


class TestAutoProcessingConfiguration:
    """Test configuration settings."""

    def test_config_defaults(self) -> None:
        """Test default configuration values."""
        from app.core.config import Settings

        # Create settings with defaults
        settings = Settings()

        assert settings.ai_auto_process_on_upload is True
        assert settings.ai_auto_process_skip_existing is True
