"""Tests for the Alembic migration that creates the users table."""

from __future__ import annotations

import importlib.util
import time
from pathlib import Path
from typing import Any

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20250923_01_create_users_table.py"
)


def test_users_table_migration_creates_expected_schema() -> None:
    spec = importlib.util.spec_from_file_location("migration_20250923_01", MIGRATION_PATH)
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
            column_info = {col["name"]: col for col in inspector.get_columns("users")}

            assert {
                "id",
                "email",
                "hashed_password",
                "created_at",
                "updated_at",
            }.issubset(column_info.keys())
            assert column_info["email"]["nullable"] is False
            unique_constraints = inspector.get_unique_constraints("users")
            assert any(
                constraint["column_names"] == ["email"] for constraint in unique_constraints
            )

            connection.execute(
                text(
                    "INSERT INTO users (email, hashed_password) VALUES "
                    "('admin@example.com', 'hash')"
                )
            )
            row = connection.execute(
                text("SELECT updated_at FROM users WHERE email = 'admin@example.com'")
            ).one()
            original_updated_at = row.updated_at
            time.sleep(1)
            connection.execute(
                text(
                    "UPDATE users SET hashed_password = 'new-hash' "
                    "WHERE email = 'admin@example.com'"
                )
            )
            refreshed_row = connection.execute(
                text("SELECT updated_at FROM users WHERE email = 'admin@example.com'")
            ).one()
            assert refreshed_row.updated_at != original_updated_at
    finally:
        migration.op = original_op
