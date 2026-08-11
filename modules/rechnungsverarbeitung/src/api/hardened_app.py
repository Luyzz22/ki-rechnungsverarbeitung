"""Production app composition with fail-closed replacement of legacy auth routes.

The oversized legacy API module still contains historical auth handlers. This
composition layer removes exactly the legacy handlers that are security-sensitive
and mounts the audited secure auth router in their place. Production containers
must target this module, not ``main:app``.
"""
from __future__ import annotations

from collections import Counter

from fastapi.routing import APIRoute

from modules.rechnungsverarbeitung.src.api.main import app
from modules.rechnungsverarbeitung.src.api.secure_auth_router import router as secure_auth_router

_REPLACED_POST_PATHS = frozenset(
    {
        "/api/v1/auth/token",
        "/api/v1/auth/forgot-password",
        "/api/v1/users/invite",
    }
)


def _is_replaced_post_route(route: object) -> bool:
    path = getattr(route, "path", None)
    methods = getattr(route, "methods", set()) or set()
    return path in _REPLACED_POST_PATHS and "POST" in methods


def _cut_over_secure_auth_routes() -> None:
    """Replace each expected legacy POST route exactly once or fail startup."""
    legacy_matches = [route for route in app.router.routes if _is_replaced_post_route(route)]
    counts = Counter(getattr(route, "path", "") for route in legacy_matches)
    expected = Counter({path: 1 for path in _REPLACED_POST_PATHS})
    if counts != expected:
        raise RuntimeError(
            "SECURITY: legacy auth route inventory changed; refusing hardened app startup"
        )

    app.router.routes[:] = [
        route for route in app.router.routes if not _is_replaced_post_route(route)
    ]
    app.include_router(secure_auth_router, prefix="/api/v1")

    active_secure_routes = [
        route
        for route in app.router.routes
        if isinstance(route, APIRoute)
        and route.path in _REPLACED_POST_PATHS
        and "POST" in route.methods
    ]
    active_counts = Counter(route.path for route in active_secure_routes)
    if active_counts != expected:
        raise RuntimeError(
            "SECURITY: secure auth route cutover is incomplete or duplicated"
        )

    unexpected_handlers = [
        route
        for route in active_secure_routes
        if route.endpoint.__module__
        != "modules.rechnungsverarbeitung.src.api.secure_auth_router"
    ]
    if unexpected_handlers:
        raise RuntimeError(
            "SECURITY: a replaced auth path is not served by secure_auth_router"
        )


_cut_over_secure_auth_routes()
