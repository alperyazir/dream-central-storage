"""Tests for storage service helpers."""

from __future__ import annotations

import io
import zipfile
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock

import pytest

from minio.error import S3Error

from app.services.storage import (
    RelocationError,
    RestorationError,
    UploadError,
    iter_zip_entries,
    list_trash_entries,
    move_prefix_to_trash,
    restore_prefix_from_trash,
    upload_book_archive,
)


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


def test_move_prefix_to_trash_relocates_objects() -> None:
    client = MagicMock()
    client.list_objects.return_value = [
        SimpleNamespace(object_name="dream/sky/chapter1.txt"),
        SimpleNamespace(object_name="dream/sky/notes/chapter2.txt"),
    ]

    report = move_prefix_to_trash(
        client=client,
        source_bucket="books",
        prefix="dream/sky",
        trash_bucket="trash",
    )

    assert report.objects_moved == 2
    copy_calls = client.copy_object.call_args_list
    assert len(copy_calls) == 2
    first_source = copy_calls[0][0][2]
    assert first_source.bucket_name == "books"
    assert first_source.object_name == "dream/sky/chapter1.txt"
    client.remove_object.assert_any_call("books", "dream/sky/chapter1.txt")
    assert report.destination_prefix == "books/dream/sky/"


def test_move_prefix_to_trash_allows_empty_prefix() -> None:
    client = MagicMock()
    client.list_objects.return_value = []

    report = move_prefix_to_trash(
        client=client,
        source_bucket="books",
        prefix="dream/sky/",
        trash_bucket="trash",
    )

    assert report.objects_moved == 0
    client.copy_object.assert_not_called()
    client.remove_object.assert_not_called()


def test_move_prefix_to_trash_raises_on_copy_failure() -> None:
    client = MagicMock()
    client.list_objects.return_value = [
        SimpleNamespace(object_name="dream/sky/file.txt")
    ]
    client.copy_object.side_effect = S3Error(
        "InternalError",
        "copy failed",
        "dream/sky/file.txt",
        "request",
        "host",
        None,
    )

    with pytest.raises(RelocationError):
        move_prefix_to_trash(
            client=client,
            source_bucket="books",
            prefix="dream/sky/",
            trash_bucket="trash",
        )


def test_move_prefix_to_trash_raises_when_listing_fails() -> None:
    client = MagicMock()
    client.list_objects.side_effect = S3Error(
        "InternalError",
        "list failed",
        "dream/sky/",
        "request",
        "host",
        None,
    )

    with pytest.raises(RelocationError):
        move_prefix_to_trash(
            client=client,
            source_bucket="books",
            prefix="dream/sky/",
            trash_bucket="trash",
        )


def test_restore_prefix_from_trash_restores_objects() -> None:
    client = MagicMock()
    client.list_objects.return_value = [
        SimpleNamespace(object_name="books/DreamPress/SkyTales/chapter1.txt"),
        SimpleNamespace(object_name="books/DreamPress/SkyTales/notes/chapter2.txt"),
    ]

    report = restore_prefix_from_trash(
        client=client,
        trash_bucket="trash",
        key="books/DreamPress/SkyTales/",
    )

    assert report.objects_moved == 2
    copy_calls = client.copy_object.call_args_list
    assert copy_calls[0][0][0] == "books"
    assert copy_calls[0][0][1] == "DreamPress/SkyTales/chapter1.txt"
    remove_calls = client.remove_object.call_args_list
    assert remove_calls[0][0][0] == "trash"


def test_restore_prefix_from_trash_raises_when_empty() -> None:
    client = MagicMock()
    client.list_objects.return_value = []

    with pytest.raises(RestorationError):
        restore_prefix_from_trash(
            client=client,
            trash_bucket="trash",
            key="books/DreamPress/SkyTales/",
        )


def test_list_trash_entries_aggregates_books_and_apps() -> None:
    client = MagicMock()
    client.list_objects.return_value = [
        SimpleNamespace(object_name="books/Press/Atlas/file1.txt", size=10),
        SimpleNamespace(object_name="books/Press/Atlas/notes/file2.txt", size=5),
        SimpleNamespace(object_name="apps/macos/1.0/app.zip", size=20),
    ]

    entries = list_trash_entries(client, "trash")

    keys = {entry.key for entry in entries}
    assert keys == {"apps/macos/1.0/", "books/Press/Atlas/"}
    book_entry = next(entry for entry in entries if entry.item_type == "book")
    assert book_entry.object_count == 2
    assert book_entry.total_size == 15
    assert book_entry.metadata == {"publisher": "Press", "book_name": "Atlas"}
