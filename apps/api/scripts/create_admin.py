"""Entry-point script delegating to app.scripts.create_admin."""

from __future__ import annotations

from app.scripts.create_admin import main


if __name__ == "__main__":  # pragma: no cover - manual invocation only
    raise SystemExit(main())
