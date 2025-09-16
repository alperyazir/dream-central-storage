from __future__ import annotations

from fastapi import HTTPException, Request


def get_current_user(request: Request):
    """Extract user context from request.state.auth if present.

    This aligns with Depends-based protection for future RBAC stories. For the
    MVP static token, middleware attaches an empty user context.
    """
    ctx = getattr(request.state, "auth", None)
    if ctx is None:
        # Middleware should have populated this on protected endpoints
        raise HTTPException(status_code=401, detail="Not authenticated")
    return ctx
