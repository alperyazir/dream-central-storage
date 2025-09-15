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

## Dev Commands

- Format: `black .`
- Lint: `ruff check .`
- Test: `pytest`

## Project Layout

```
app/
  main.py
  tests/
    unit/
      test_health.py
```

Refer to the root repo docs under `docs/architecture/` for broader architecture, testing standards, and deployment notes.
