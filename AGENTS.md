# Repository Guidelines

## Project Structure & Module Organization
- `docs/architecture/`: System design, coding standards, test strategy, and deployment notes. Start with `docs/architecture/index.md`.
- `docs/prd/`: Product requirements and epics used for planning.
- `.bmad-core/`: BMAD method core files (agents, tasks, templates, checklists). Treat as tooling; avoid ad-hoc edits.
- `agents/` and `teams/`: Role presets and team compositions for Codex/BMAD workflows.
- `expansion-packs/`: Optional agent sets for specialized domains.

## Build, Test, and Development Commands
- Validate BMAD config: `npx bmad-method validate`
- Regenerate BMAD assets: `npx bmad-method install -f -i codex`
- Launch Codex CLI: `codex` (reference roles, e.g., “As dev, …”).
- Service code runs in its own repo; follow `docs/architecture/*` for FastAPI build/run specifics.

## Coding Style & Naming Conventions
- Python (service repos): Follow `docs/architecture/coding-standards.md` — Black formatting, Ruff linting, PEP 8, full type hints, Pydantic schemas, centralized config access.
- Docs: Lowercase, kebab-case filenames (e.g., `high-level-architecture.md`). Keep headings scoped and concise.
- Indentation: 4 spaces for Python; wrap long Markdown lines sensibly.

## Testing Guidelines
- Strategy and coverage targets live in `docs/architecture/test-strategy-and-standards.md` (pytest, 80% coverage, unit/integration split).
- Naming: `test_*.py`; place tests under `app/tests/{unit|integration}/` in service repos.
- Run example: `pytest -q` (add coverage flags where configured).

## Commit & Pull Request Guidelines
- Commits: Imperative mood, focused scope. Prefer Conventional Commits prefixes: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- PRs: Include a clear description, linked issues, scope of change, and verification notes. Add screenshots for UI or sample requests/responses for API.
- Keep PRs small where possible and update related docs in the same PR.

## Security & Configuration Tips
- Never commit secrets. Use environment variables and `.env` files ignored by Git.
- For service repos, document required env vars (e.g., `DATABASE_URL`, `MINIO_*`) and provide a sample `docker-compose.yml` per `docs/architecture/infrastructure-and-deployment.md`.

