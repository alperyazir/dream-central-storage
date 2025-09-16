from __future__ import annotations

from collections.abc import Iterable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


class AuthMiddleware(BaseHTTPMiddleware):
    """Bearer token authentication middleware with public path bypass.

    - Public paths bypass authentication checks.
    - 401 when Authorization header is missing/malformed; includes WWW-Authenticate: Bearer
    - 403 when Bearer token provided but unauthorized
    """

    def __init__(
        self,
        app,
        *,
        token: str | None,
        public_paths: Iterable[str] = (),
    ) -> None:
        super().__init__(app)
        self._token = token or ""
        # normalize public paths as exact path strings
        self._public = set(public_paths)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Bypass for explicitly public paths
        if request.url.path in self._public:
            return await call_next(request)

        # Extract and validate Authorization header
        auth = request.headers.get("authorization")
        if not auth:
            return self._unauthorized()

        try:
            scheme, token = auth.split(" ", 1)
        except ValueError:
            return self._unauthorized()

        if scheme.lower() != "bearer":
            return self._unauthorized()

        if not token:
            return self._unauthorized()

        # Static token authorization (MVP)
        if self._token and token != self._token:
            return self._forbidden()

        # Attach minimal auth context for future RBAC
        request.state.auth = {
            "sub": None,
            "roles": [],
            "scopes": [],
            "token_type": "static",
        }
        return await call_next(request)

    @staticmethod
    def _unauthorized() -> Response:
        return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})

    @staticmethod
    def _forbidden() -> Response:
        return Response(status_code=403)
