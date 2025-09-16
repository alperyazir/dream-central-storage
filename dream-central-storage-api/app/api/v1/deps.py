from __future__ import annotations

from fastapi import HTTPException, Request


def get_current_user(request: Request):
    ctx = getattr(request.state, "auth", None)
    if ctx is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return ctx
