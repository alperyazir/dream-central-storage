"""Utility script for inserting the initial administrator account."""

from __future__ import annotations

import argparse
import getpass
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_password_hash
from app.db import SessionLocal
from app.models.user import User
from app.repositories.user import UserRepository


def create_admin_user(session: Session, *, email: str, password: str) -> User:
    """Persist an administrator with a securely hashed password."""

    repository = UserRepository()
    normalized_email = email.strip().lower()
    existing = repository.get_by_email(session, normalized_email)
    if existing is not None:
        raise ValueError(f"An administrator with email {normalized_email!r} already exists")

    user = User(email=normalized_email, hashed_password=create_password_hash(password))
    repository.add(session, user)
    session.commit()
    session.refresh(user)
    return user


def _resolve_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create initial admin user")
    parser.add_argument("--email", help="Email address for the admin user")
    parser.add_argument(
        "--password",
        help="Password for the admin user (omit to securely prompt)",
    )
    parser.add_argument(
        "--prompt",
        action="store_true",
        help="Force interactive prompts for email and password",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _resolve_cli_args(argv)

    email = args.email
    password = args.password

    if args.prompt or not email:
        email = input("Admin email: ").strip()
    if not email:
        raise SystemExit("Email must be provided")

    if args.prompt or password is None:
        password = getpass.getpass("Admin password: ")
    if not password:
        raise SystemExit("Password must be provided")

    with SessionLocal() as session:
        try:
            user = create_admin_user(session, email=email, password=password)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        except IntegrityError as exc:
            session.rollback()
            raise SystemExit("Failed to create admin user due to database constraint") from exc

    print(f"Admin user created with id={user.id}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation only
    raise SystemExit(main())
