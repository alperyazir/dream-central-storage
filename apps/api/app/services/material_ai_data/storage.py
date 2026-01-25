"""Storage service for material AI data.

Handles saving and loading AI-processed data for teacher materials.
Storage structure:
    {teacher_id}/materials/{material_name}/ai-data/
        text/
            page_001.txt, page_002.txt, ...
            extraction_metadata.json
        modules/
            module_001.json, ...
            metadata.json
        vocabulary.json
        audio/
            vocabulary/{lang}/word_001.mp3, ...
        metadata.json (overall processing status)
"""

from __future__ import annotations

import json
import logging
from io import BytesIO
from typing import Any, TYPE_CHECKING

from app.core.config import get_settings
from app.services.minio import get_minio_client
from app.services.material_extraction.models import MaterialExtractionResult

if TYPE_CHECKING:
    from minio import Minio

logger = logging.getLogger(__name__)


class MaterialAIDataStorage:
    """Service for storing and retrieving material AI data."""

    def __init__(self, minio_client: Minio | None = None) -> None:
        """Initialize the storage service.

        Args:
            minio_client: Optional MinIO client
        """
        self._client = minio_client
        self._settings = get_settings()

    @property
    def client(self) -> Minio:
        """Get MinIO client."""
        if self._client is None:
            self._client = get_minio_client(self._settings)
        return self._client

    @property
    def bucket(self) -> str:
        """Get the teachers bucket name."""
        return self._settings.minio_teachers_bucket

    def _get_ai_data_prefix(self, teacher_id: str, material_name: str) -> str:
        """Get the AI data prefix for a material.

        Args:
            teacher_id: Teacher ID
            material_name: Material filename

        Returns:
            AI data prefix path
        """
        # Remove extension from material_name for folder
        base_name = material_name.rsplit(".", 1)[0] if "." in material_name else material_name
        return f"{teacher_id}/materials/{base_name}/ai-data"

    def save_extracted_text(
        self,
        extraction_result: MaterialExtractionResult,
    ) -> dict[str, Any]:
        """Save extracted text pages to storage.

        Args:
            extraction_result: Extraction result with pages

        Returns:
            Dict with saved file paths
        """
        prefix = self._get_ai_data_prefix(
            extraction_result.teacher_id,
            extraction_result.material_name,
        )
        text_prefix = f"{prefix}/text"

        saved_files: list[str] = []

        # Save each page
        for page in extraction_result.pages:
            page_path = f"{text_prefix}/page_{page.page_number:03d}.txt"
            self._save_text(page_path, page.text)
            saved_files.append(page_path)

        # Save extraction metadata
        metadata = {
            "material_id": extraction_result.material_id,
            "teacher_id": extraction_result.teacher_id,
            "material_name": extraction_result.material_name,
            "file_type": extraction_result.file_type.value,
            "total_pages": extraction_result.total_pages,
            "total_word_count": extraction_result.total_word_count,
            "method": extraction_result.method.value,
        }
        metadata_path = f"{text_prefix}/extraction_metadata.json"
        self._save_json(metadata_path, metadata)
        saved_files.append(metadata_path)

        logger.info(
            "Saved extracted text for %s: %d files",
            extraction_result.material_name,
            len(saved_files),
        )

        return {
            "text_files": saved_files,
            "metadata": metadata_path,
        }

    def save_analysis_result(
        self,
        teacher_id: str,
        material_name: str,
        modules: list[dict[str, Any]],
        vocabulary: list[dict[str, Any]],
        analysis_metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Save AI analysis results to storage.

        Args:
            teacher_id: Teacher ID
            material_name: Material filename
            modules: List of module data dicts
            vocabulary: List of vocabulary word dicts
            analysis_metadata: Analysis metadata

        Returns:
            Dict with saved file paths
        """
        prefix = self._get_ai_data_prefix(teacher_id, material_name)
        saved_paths: dict[str, Any] = {}

        # Save modules
        if modules:
            modules_prefix = f"{prefix}/modules"
            saved_modules = []
            for i, module in enumerate(modules, 1):
                module_path = f"{modules_prefix}/module_{i:03d}.json"
                self._save_json(module_path, module)
                saved_modules.append(module_path)

            # Save modules metadata
            modules_meta = {
                "module_count": len(modules),
                "modules": [{"id": m.get("id", i), "title": m.get("title", "")} for i, m in enumerate(modules, 1)],
            }
            modules_meta_path = f"{modules_prefix}/metadata.json"
            self._save_json(modules_meta_path, modules_meta)

            saved_paths["modules"] = saved_modules
            saved_paths["modules_metadata"] = modules_meta_path

        # Save vocabulary
        if vocabulary:
            vocab_path = f"{prefix}/vocabulary.json"
            vocab_data = {
                "words": vocabulary,
                "total_count": len(vocabulary),
                "language": analysis_metadata.get("primary_language", "en"),
                "translation_language": analysis_metadata.get("translation_language", "tr"),
            }
            self._save_json(vocab_path, vocab_data)
            saved_paths["vocabulary"] = vocab_path

        # Save overall metadata
        metadata_path = f"{prefix}/metadata.json"
        self._save_json(metadata_path, analysis_metadata)
        saved_paths["metadata"] = metadata_path

        logger.info(
            "Saved analysis results for %s: %d modules, %d vocabulary words",
            material_name,
            len(modules),
            len(vocabulary),
        )

        return saved_paths

    def load_extracted_text(
        self,
        teacher_id: str,
        material_name: str,
    ) -> dict[int, str]:
        """Load extracted text pages from storage.

        Args:
            teacher_id: Teacher ID
            material_name: Material filename

        Returns:
            Dict mapping page numbers to text content
        """
        prefix = self._get_ai_data_prefix(teacher_id, material_name)
        text_prefix = f"{prefix}/text"

        pages: dict[int, str] = {}

        # Load extraction metadata to get page count
        try:
            metadata = self._load_json(f"{text_prefix}/extraction_metadata.json")
            total_pages = metadata.get("total_pages", 0)

            for page_num in range(1, total_pages + 1):
                page_path = f"{text_prefix}/page_{page_num:03d}.txt"
                try:
                    text = self._load_text(page_path)
                    if text.strip():
                        pages[page_num] = text
                except Exception:
                    continue

        except Exception as e:
            logger.warning("Failed to load extracted text: %s", e)

        return pages

    def load_vocabulary(
        self,
        teacher_id: str,
        material_name: str,
    ) -> dict[str, Any]:
        """Load vocabulary data from storage.

        Args:
            teacher_id: Teacher ID
            material_name: Material filename

        Returns:
            Vocabulary data dict
        """
        prefix = self._get_ai_data_prefix(teacher_id, material_name)
        vocab_path = f"{prefix}/vocabulary.json"

        try:
            return self._load_json(vocab_path)
        except Exception as e:
            logger.warning("Failed to load vocabulary: %s", e)
            return {"words": [], "total_count": 0}

    def load_metadata(
        self,
        teacher_id: str,
        material_name: str,
    ) -> dict[str, Any]:
        """Load processing metadata from storage.

        Args:
            teacher_id: Teacher ID
            material_name: Material filename

        Returns:
            Metadata dict
        """
        prefix = self._get_ai_data_prefix(teacher_id, material_name)
        metadata_path = f"{prefix}/metadata.json"

        try:
            return self._load_json(metadata_path)
        except Exception as e:
            logger.warning("Failed to load metadata: %s", e)
            return {}

    def cleanup_ai_data(
        self,
        teacher_id: str,
        material_name: str,
    ) -> int:
        """Delete all AI data for a material.

        Args:
            teacher_id: Teacher ID
            material_name: Material filename

        Returns:
            Number of objects deleted
        """
        prefix = self._get_ai_data_prefix(teacher_id, material_name)

        deleted = 0
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            for obj in objects:
                self.client.remove_object(self.bucket, obj.object_name)
                deleted += 1

            logger.info("Deleted %d AI data objects for %s", deleted, material_name)
        except Exception as e:
            logger.error("Failed to cleanup AI data: %s", e)

        return deleted

    def save_audio_file(
        self,
        teacher_id: str,
        material_name: str,
        word: str,
        language: str,
        audio_data: bytes,
    ) -> str:
        """Save audio file for a vocabulary word.

        Args:
            teacher_id: Teacher ID
            material_name: Material filename
            word: Vocabulary word
            language: Language code
            audio_data: Audio file bytes

        Returns:
            Saved file path
        """
        prefix = self._get_ai_data_prefix(teacher_id, material_name)
        # Sanitize word for filename
        safe_word = "".join(c if c.isalnum() or c in "-_" else "_" for c in word)
        audio_path = f"{prefix}/audio/vocabulary/{language}/{safe_word}.mp3"

        self._save_bytes(audio_path, audio_data, "audio/mpeg")
        return audio_path

    def _save_text(self, path: str, content: str) -> None:
        """Save text content to storage."""
        data = content.encode("utf-8")
        stream = BytesIO(data)
        self.client.put_object(
            self.bucket,
            path,
            stream,
            len(data),
            content_type="text/plain; charset=utf-8",
        )

    def _save_json(self, path: str, data: dict | list) -> None:
        """Save JSON data to storage."""
        content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        stream = BytesIO(content)
        self.client.put_object(
            self.bucket,
            path,
            stream,
            len(content),
            content_type="application/json; charset=utf-8",
        )

    def _save_bytes(self, path: str, data: bytes, content_type: str) -> None:
        """Save binary data to storage."""
        stream = BytesIO(data)
        self.client.put_object(
            self.bucket,
            path,
            stream,
            len(data),
            content_type=content_type,
        )

    def _load_text(self, path: str) -> str:
        """Load text content from storage."""
        response = self.client.get_object(self.bucket, path)
        data = response.read()
        response.close()
        response.release_conn()
        return data.decode("utf-8")

    def _load_json(self, path: str) -> dict:
        """Load JSON data from storage."""
        text = self._load_text(path)
        return json.loads(text)


# Module-level singleton
_storage: MaterialAIDataStorage | None = None


def get_material_ai_storage() -> MaterialAIDataStorage:
    """Get or create the material AI data storage singleton."""
    global _storage
    if _storage is None:
        _storage = MaterialAIDataStorage()
    return _storage
