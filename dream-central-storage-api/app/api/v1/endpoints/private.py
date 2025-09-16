from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user

router = APIRouter(prefix="/api/v1/private", tags=["private"])


@router.get("/ping", dependencies=[Depends(get_current_user)])
def private_ping() -> dict[str, str]:
    return {"status": "ok"}
