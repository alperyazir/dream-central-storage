# Local Development & Deployment Brief

## Prerequisites
- Docker and Docker Compose v2
- Python 3.11+ (for running standalone scripts such as `backup_minio.py`)
- Node.js 20+ and pnpm (for admin panel development)
- Access credentials for MinIO, PostgreSQL, and any external services when deploying to the VPS

## Running Locally
1. From the repository root, start the stack:
   ```bash
   cd infrastructure
   docker compose up --build
   ```
   This launches the FastAPI API (`http://localhost:8000`), MinIO (`http://localhost:9000`), PostgreSQL, and Nginx reverse proxy (`http://localhost:8080`).
2. Open the admin panel frontend (served through Nginx). Authenticate using credentials created in seeding scripts or via the API.
3. Run backend tests at any time:
   ```bash
   cd apps/api
   pytest
   ```
4. Run frontend tests:
   ```bash
   cd apps/admin-panel
   pnpm install
   pnpm test -- --run
   ```
5. Enable monitoring locally using the optional profile:
   ```bash
   cd infrastructure
   docker compose --profile monitoring up -d prometheus grafana
   ```
   - Prometheus target UI: `http://localhost:9091/targets`
   - Grafana dashboard: `http://localhost:3000` (default admin/admin credentials)

## Deploying to the VPS
1. Pull the latest changes on the server:
   ```bash
   git pull origin main
   ```
2. Copy updated configuration assets:
   - `infrastructure/docker-compose.yml`
   - `infrastructure/monitoring/prometheus.yml`
   - `infrastructure/monitoring/dashboards/dream-central-api.json`
3. Ensure environment files contain production secrets:
   - `apps/api/.env`
   - `/etc/dream-central-storage/backup.env` (for backup script)
4. Recreate core services without downtime:
   ```bash
   cd /opt/dream-central/infrastructure
   docker compose pull
   docker compose up -d api nginx
   ```
5. Run database migrations if necessary:
   ```bash
   cd /opt/dream-central/apps/api
   alembic upgrade head
   ```
6. Start/refresh monitoring stack (optional):
   ```bash
   docker compose --profile monitoring up -d prometheus grafana
   ```
7. Validate deployment:
   - API health: `curl http://localhost:8000/health`
   - Admin panel: verify login and core flows
   - Backups: trigger `/usr/local/bin/dream-backup --log-path /tmp/minio-backup.log`
   - Monitoring: confirm Prometheus scrape target and Grafana dashboard load

## Ongoing Operations
- Backups run via cron; review `/var/log/minio-backup.log` for success/failure.
- Monitoring runbook (`docs/operations/monitoring-runbook.md`) covers troubleshooting.
- Review `docs/operations/minio-backup-runbook.md` for recovery drills and credential rotation.
