from __future__ import annotations

from collections.abc import Iterable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, token: str | None, public_paths: Iterable[str] = ()) -> None:
        super().__init__(app)
        self._token = token or ""
        self._public = set(public_paths)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in self._public:
            return await call_next(request)

        auth = request.headers.get("authorization")
        if not auth:
            return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})
        try:
            scheme, token = auth.split(" ", 1)
        except ValueError:
            return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})
        if scheme.lower() != "bearer" or not token:
            return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})

        if self._token and token != self._token:
            return Response(status_code=403)

        request.state.auth = {"sub": None, "roles": [], "scopes": [], "token_type": "static"}
        return await call_next(request)
