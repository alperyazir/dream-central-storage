#!/usr/bin/env bash
# Wrapper to execute the MinIO backup script with optional environment overrides.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "${SCRIPT_DIR}/backup_minio.py" "$@"
