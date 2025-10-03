# MinIO Backup Runbook

## Overview

Automated backups mirror the primary MinIO buckets (`books`, `apps`, and `trash`) to an off-site object storage bucket using the MinIO `mc` CLI. The job runs daily via cron and writes structured logs for auditing and troubleshooting.

## Prerequisites

- `mc` (MinIO Client) installed on the VPS (https://min.io/docs/minio/linux/reference/minio-mc.html).
- Python 3.11+ available for executing the backup script.
- Off-site object storage credentials (can be another MinIO deployment or S3-compatible provider).
- Environment file `/etc/dream-central-storage/backup.env` readable by cron with the following variables:

```
MINIO_SOURCE_ENDPOINT="https://minio.internal.example.com"
MINIO_SOURCE_ACCESS_KEY="source-access-key"
MINIO_SOURCE_SECRET_KEY="source-secret-key"
BACKUP_TARGET_ENDPOINT="https://s3.backup.example.com"
BACKUP_TARGET_ACCESS_KEY="backup-access-key"
BACKUP_TARGET_SECRET_KEY="backup-secret-key"
BACKUP_TARGET_BUCKET="dream-central-storage-backups"
MINIO_BACKUP_BUCKETS="books,apps,trash"
MINIO_BACKUP_LOG="/var/log/minio-backup.log"
MC_PATH="/usr/local/bin/mc"
```

## Installation Steps

1. Copy `infrastructure/scripts/backup_minio.py` and `infrastructure/scripts/dream-backup.sh` to `/usr/local/bin/`.
2. Make both scripts executable (`chmod +x /usr/local/bin/backup_minio.py /usr/local/bin/dream-backup.sh`).
3. Place the environment file at `/etc/dream-central-storage/backup.env` with secure permissions (`chmod 600`).
4. Install the cron definition by copying `infrastructure/cron/dream-storage-backup` to `/etc/cron.d/dream-storage-backup`.
5. Reload cron (`systemctl reload cron`) if required by the distribution.

## Manual Execution

To run a one-off backup (e.g., before maintenance):

```
sudo MINIO_BACKUP_LOG=/var/log/minio-backup.manual.log /usr/local/bin/dream-backup --log-path /var/log/minio-backup.manual.log
```

Review `/var/log/minio-backup.manual.log` for success messages and JSON mirror events.

## Monitoring & Logs

- Primary log file: `/var/log/minio-backup.log` (configurable via `MINIO_BACKUP_LOG`).
- Cron wrapper log: `/var/log/minio-backup.cron.log` (captures stdout/stderr from cron job).
- Each run logs `Starting mirror` and `Completed mirror` entries per bucket along with any JSON payloads emitted by `mc`.

## Failure Handling

1. Inspect `/var/log/minio-backup.log` for entries with `Backup failed` or `Mirror failed`.
2. Confirm off-site credentials and network connectivity.
3. Re-run the job manually with `--log-path` pointing to a temporary file for additional diagnostics.
4. If repeated failures occur, escalate with the captured logs to operations leadership.

## Restore Drill (Quarterly)

1. Select a sample bucket (e.g., `books`).
2. Use `mc ls backup/dream-central-storage-backups/books` to verify snapshot availability.
3. Download a small sample file and compare checksums with production to validate integrity.
4. Record results in the operations logbook.

## Configuration Changes

Whenever adding or removing MinIO buckets, update `MINIO_BACKUP_BUCKETS` in the environment file and re-run the backup script once to establish destination paths.

