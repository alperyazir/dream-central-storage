"""Authentication endpoints for the Dream Central API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.db import get_db
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])
_user_repository = UserRepository()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate an administrator and return a JWT access token."""

    email = payload.email.strip().lower()
    user = _user_repository.get_by_email(db, email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    settings = get_settings()
    token = create_access_token(subject=str(user.id), settings=settings)
    return TokenResponse(access_token=token)
