"""Tests for the Alembic migration that creates the books table."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20250922_01_create_books_table.py"
)


def test_books_table_migration_creates_expected_schema() -> None:
    spec = importlib.util.spec_from_file_location("migration_20250922_01", MIGRATION_PATH)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    original_op: Any = migration.op

    try:
        with engine.begin() as connection:
            context = MigrationContext.configure(connection=connection)
            migration.op = Operations(context)

            migration.upgrade()

            inspector = inspect(connection)
            column_info = {col["name"]: col for col in inspector.get_columns("books")}

            assert {
                "id",
                "publisher",
                "book_name",
                "language",
                "category",
                "version",
                "status",
                "created_at",
                "updated_at",
            }.issubset(column_info.keys())
            assert column_info["version"]["nullable"] is True
            assert column_info["status"]["default"] == "'draft'"

            connection.execute(
                text(
                    "INSERT INTO books (publisher, book_name, language, category) VALUES "
                    "('Test Publisher', 'Example Book', 'en', 'fiction')"
                )
            )
            row = connection.execute(
                text("SELECT status, version, created_at, updated_at FROM books")
            ).one()
            assert row.status == "draft"
            assert row.version is None
            assert row.created_at is not None
            assert row.updated_at is not None
    finally:
        migration.op = original_op
