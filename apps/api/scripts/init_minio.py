"""Entry point for MinIO bucket initialization."""

from __future__ import annotations

from app.scripts.init_minio import main


if __name__ == "__main__":  # pragma: no cover - manual execution only
    raise SystemExit(main())
