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

## Authentication (Static Bearer)

Static bearer authentication is enabled via middleware.

- Public endpoints (no auth required):
  - `GET /health`
  - `GET /storage/health`
- Protected endpoints require a bearer token.

Setup:

- Option A (recommended): create `.env`
  - `cp .env.example .env` and edit values
  - `uvicorn app.main:app --reload`
- Option B: export in shell
  - `export AUTH_BEARER_TOKEN='secret-token'`
  - `uvicorn app.main:app --reload`

## Upload Application Build (Story 1.4)

Secure endpoint to upload a FlowBook app build by platform and version.

- Route: `POST /api/v1/apps/`
- Auth: Bearer token required (see Authentication)
- Form fields:
  - `version`: string (e.g., `1.0.0`)
  - `platform`: one of `linux`, `macos`, `windows` (case-insensitive)
  - `file`: zip file (multipart)
- Storage path: `apps/{platform}/{version}/flowbook.zip`

Example:

```
# If using .env, just run uvicorn; otherwise export vars
uvicorn app.main:app --reload

curl -i -X POST \
  -H "Authorization: Bearer $AUTH_BEARER_TOKEN" \
  -F version=1.0.0 \
  -F platform=linux \
  -F file=@flowbook.zip \
localhost:8000/api/v1/apps/
```

### Large File Uploads

- The service streams uploads directly to S3/MinIO and does not load the entire file into memory.
- Multipart uploads are used automatically with 10 MB parts.
  - This keeps memory usage low and supports very large files.
  - Adjusting part size is not yet configurable (defaults to 10 MB).
- Ensure your reverse proxy allows large bodies if needed:
  - Nginx: `client_max_body_size 2G;`
  - Traefik: `traefik.http.middlewares.limit.buffering.maxRequestBodyBytes`
- Application-level size limits are not enforced; add them at the proxy if required.
