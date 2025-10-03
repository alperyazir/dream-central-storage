"""Routes serving Prometheus metrics."""

from __future__ import annotations

from fastapi import APIRouter, Response

from .middleware import render_metrics

router = APIRouter(tags=["Monitoring"])


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    """Expose collected metrics for Prometheus scraping."""

    payload = render_metrics()
    return Response(content=payload, media_type="text/plain; version=0.0.4")
