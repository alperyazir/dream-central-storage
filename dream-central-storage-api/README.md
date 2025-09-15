# Dream Central Storage API

FastAPI service that provides health checks and will host endpoints for managing application builds and book datasets.

## Run Locally

- Install dependencies (example using pip):
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -e '.[dev]'`
- Start server:
  - `uvicorn app.main:app --reload`
- Health check:
  - `curl -s localhost:8000/health`
  - Expected: `{ "status": "ok" }`
 - Storage health:
   - `curl -s localhost:8000/storage/health`
   - Reports S3 connectivity and bucket availability

## Dev Commands

- Format: `black .`
- Lint: `ruff check .`
- Test (unit): `pytest -m "not integration"`
- Test (all, with MinIO running): `pytest`

## Project Layout

```
app/
  main.py
  tests/
    unit/
      test_health.py
      test_storage_health.py
```

Refer to the root repo docs under `docs/architecture/` for broader architecture, testing standards, and deployment notes.

## Configuration (Story 1.2: S3 Storage)

Set environment variables for S3/MinIO connectivity:

- `S3_ENDPOINT` or `MINIO_ENDPOINT` (e.g., `http://localhost:9000`)
- `S3_ACCESS_KEY` or `MINIO_ACCESS_KEY`
- `S3_SECRET_KEY` or `MINIO_SECRET_KEY`
- `S3_BUCKET` or `MINIO_BUCKET`
- `S3_SECURE` (optional: `true`/`false`, default `false`)

On startup, the API attempts to connect to S3 and logs the result. You can also check `/storage/health` for a JSON status report.

## Run MinIO Locally (Docker)

One-liner:

```
docker run --rm -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin -e MINIO_ROOT_PASSWORD=minioadmin \
  -v "$(pwd)/.minio-data:/data" --name dcs-minio \
  minio/minio:RELEASE.2024-08-17T01-24-54Z server /data --console-address ":9001"
```

Or via compose (from `dream-central-storage-api/`):

```
docker compose -f docker-compose.minio.yml up
```

Export env vars (example):

```
export S3_ENDPOINT='http://localhost:9000' \
  S3_ACCESS_KEY='minioadmin' \
  S3_SECRET_KEY='minioadmin' \
  S3_BUCKET='dream-assets' \
  S3_SECURE='false'
```

Run integration tests (requires MinIO running):

```
pytest -m integration -q
```
