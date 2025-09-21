# Dream Central Storage API

FastAPI backend service for Dream Central Storage. This package exposes a foundational application skeleton including configuration management, database wiring, and a health-check endpoint.

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Run tests with:

```bash
pytest
```
