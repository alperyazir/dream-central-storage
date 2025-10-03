#!/usr/bin/env python3
"""Synchronise MinIO buckets to an off-site backup target using the `mc` CLI.

The script reads configuration from environment variables or CLI arguments,
creates the required MinIO client aliases, mirrors each bucket to the backup
endpoint, and emits structured log messages for auditing.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

LOGGER = logging.getLogger("backup")


class BackupError(RuntimeError):
    """Raised when the backup process cannot be completed."""


@dataclass(frozen=True)
class BackupConfig:
    """Configuration required to execute a backup run."""

    mc_path: str
    source_endpoint: str
    source_access_key: str
    source_secret_key: str
    backup_endpoint: str
    backup_access_key: str
    backup_secret_key: str
    backup_bucket: str
    buckets: tuple[str, ...]
    log_path: Path

    @staticmethod
    def from_env_and_args(args: argparse.Namespace) -> "BackupConfig":
        def env_or_arg(name: str, arg_value: str | None) -> str:
            env_value = os.getenv(name)
            value = arg_value or env_value
            if not value:
                raise BackupError(f"Missing configuration value for {name}")
            return value

        buckets = tuple(
            bucket.strip()
            for bucket in (args.buckets or os.getenv("MINIO_BACKUP_BUCKETS", "")).split(",")
            if bucket.strip()
        )

        if not buckets:
            buckets = ("books", "apps", "trash")

        log_path = Path(args.log_path or os.getenv("MINIO_BACKUP_LOG", "/var/log/minio-backup.log"))

        return BackupConfig(
            mc_path=args.mc_path or os.getenv("MC_PATH", "mc"),
            source_endpoint=env_or_arg("MINIO_SOURCE_ENDPOINT", args.source_endpoint),
            source_access_key=env_or_arg("MINIO_SOURCE_ACCESS_KEY", args.source_access_key),
            source_secret_key=env_or_arg("MINIO_SOURCE_SECRET_KEY", args.source_secret_key),
            backup_endpoint=env_or_arg("BACKUP_TARGET_ENDPOINT", args.backup_endpoint),
            backup_access_key=env_or_arg("BACKUP_TARGET_ACCESS_KEY", args.backup_access_key),
            backup_secret_key=env_or_arg("BACKUP_TARGET_SECRET_KEY", args.backup_secret_key),
            backup_bucket=env_or_arg("BACKUP_TARGET_BUCKET", args.backup_bucket),
            buckets=buckets,
            log_path=log_path,
        )


CompletedProcess = subprocess.CompletedProcess[str]
Runner = Callable[[Sequence[str]], CompletedProcess]


def _configure_logging(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOGGER.setLevel(logging.INFO)
    LOGGER.addHandler(handler)


def _run_command(command: Sequence[str]) -> CompletedProcess:
    LOGGER.debug("Executing command", extra={"command": list(command)})
    return subprocess.run(  # pylint: disable=subprocess-run-check
        list(command),
        check=True,
        capture_output=True,
        text=True,
    )


def _ensure_alias(alias: str, endpoint: str, access_key: str, secret_key: str, *, runner: Runner, mc_path: str) -> None:
    command = [mc_path, "alias", "set", alias, endpoint, access_key, secret_key]
    runner(command)
    LOGGER.info("Configured MinIO alias", extra={"alias": alias, "endpoint": endpoint})


def _ensure_bucket(alias: str, bucket: str, *, runner: Runner, mc_path: str) -> None:
    command = [mc_path, "mb", "--ignore-existing", f"{alias}/{bucket}"]
    runner(command)
    LOGGER.info("Ensured bucket exists", extra={"alias": alias, "bucket": bucket})


def _mirror_bucket(source_alias: str, dest_alias: str, bucket: str, *, runner: Runner, mc_path: str) -> None:
    command = [
        mc_path,
        "mirror",
        "--json",
        "--overwrite",
        "--remove",
        f"{source_alias}/{bucket}",
        f"{dest_alias}/{bucket}",
    ]

    try:
        result = runner(command)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - raised via runner
        LOGGER.error(
            "Mirror failed",
            extra={"bucket": bucket, "command": command, "stderr": exc.stderr},
        )
        raise BackupError(f"Mirror failed for bucket '{bucket}'") from exc

    event_lines = [line for line in result.stdout.splitlines() if line.strip()]
    for line in event_lines:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {"message": line}
        payload.update({"bucket": bucket, "event": "mirror"})
        LOGGER.info("Mirror output", extra=payload)


def run_backup(config: BackupConfig, *, runner: Runner = _run_command) -> None:
    source_alias = "source"
    backup_alias = "backup"

    _ensure_alias(source_alias, config.source_endpoint, config.source_access_key, config.source_secret_key, runner=runner, mc_path=config.mc_path)
    _ensure_alias(backup_alias, config.backup_endpoint, config.backup_access_key, config.backup_secret_key, runner=runner, mc_path=config.mc_path)

    _ensure_bucket(backup_alias, config.backup_bucket, runner=runner, mc_path=config.mc_path)

    for bucket in config.buckets:
        destination_bucket_path = f"{config.backup_bucket}/{bucket}"
        _ensure_bucket(backup_alias, destination_bucket_path, runner=runner, mc_path=config.mc_path)
        LOGGER.info(
            "Starting mirror",
            extra={"bucket": bucket, "destination": destination_bucket_path},
        )
        _mirror_bucket(f"{source_alias}", f"{backup_alias}/{config.backup_bucket}", bucket, runner=runner, mc_path=config.mc_path)
        LOGGER.info(
            "Completed mirror",
            extra={"bucket": bucket, "destination": destination_bucket_path},
        )


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Back up MinIO buckets using the mc CLI")
    parser.add_argument("--mc-path", help="Path to the mc executable")
    parser.add_argument("--source-endpoint", help="Source MinIO endpoint URL")
    parser.add_argument("--source-access-key", help="Access key for the source MinIO instance")
    parser.add_argument("--source-secret-key", help="Secret key for the source MinIO instance")
    parser.add_argument("--backup-endpoint", help="Backup target endpoint URL")
    parser.add_argument("--backup-access-key", help="Access key for the backup target")
    parser.add_argument("--backup-secret-key", help="Secret key for the backup target")
    parser.add_argument("--backup-bucket", help="Top-level bucket/container on the backup target to store mirrored data")
    parser.add_argument("--buckets", help="Comma-separated list of buckets to mirror (defaults to books,apps,trash)")
    parser.add_argument("--log-path", help="Log file path (defaults to /var/log/minio-backup.log)")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    try:
        args = parse_args(argv)
        config = BackupConfig.from_env_and_args(args)
        _configure_logging(config.log_path)
        LOGGER.info("Starting MinIO backup", extra={"buckets": list(config.buckets)})
        run_backup(config)
        LOGGER.info("Backup complete")
        return 0
    except BackupError as exc:
        LOGGER.error("Backup failed", extra={"error": str(exc)})
        return 1
    except Exception as exc:  # pragma: no cover - defensive logging of unexpected errors
        LOGGER.exception("Unexpected backup failure: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
