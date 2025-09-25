"""Tests for storage service helpers."""

from __future__ import annotations

import io
import zipfile
from unittest.mock import ANY, MagicMock

import pytest

from app.services.storage import UploadError, iter_zip_entries, upload_book_archive


@pytest.fixture()
def sample_archive_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("chapter1.txt", "Once upon a time")
        archive.writestr("chapter2.txt", "The end")
    return buffer.getvalue()


def test_iter_zip_entries_skips_directories() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("folder/", "")
        archive.writestr("folder/file.txt", "content")

    archive = zipfile.ZipFile(io.BytesIO(buffer.getvalue()))
    entries = list(iter_zip_entries(archive))
    assert len(entries) == 1
    assert entries[0].filename == "folder/file.txt"


def test_upload_book_archive_puts_files(sample_archive_bytes: bytes) -> None:
    client = MagicMock()

    manifest = upload_book_archive(
        client=client,
        archive_bytes=sample_archive_bytes,
        bucket="books",
        object_prefix="dream/sky/",
    )

    assert len(manifest) == 2
    client.put_object.assert_any_call(
        "books",
        "dream/sky/chapter1.txt",
        ANY,
        length=len("Once upon a time"),
        content_type="application/octet-stream",
    )


def test_upload_book_archive_raises_for_invalid_zip() -> None:
    client = MagicMock()

    with pytest.raises(UploadError):
        upload_book_archive(
            client=client,
            archive_bytes=b"not a zip",
            bucket="books",
            object_prefix="dream/sky/",
        )
