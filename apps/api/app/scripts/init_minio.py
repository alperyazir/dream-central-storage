"""CLI utility to bootstrap required MinIO buckets."""

from __future__ import annotations

import argparse
import sys

from app.core.config import get_settings
from app.services import ensure_buckets, get_minio_client


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap MinIO buckets")
    parser.parse_args(argv)

    settings = get_settings()
    client = get_minio_client(settings)
    ensure_buckets(client, settings.minio_buckets)
    print("MinIO buckets verified")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual execution only
    sys.exit(main())
