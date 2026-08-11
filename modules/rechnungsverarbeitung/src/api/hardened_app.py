"""Production app composition with fail-closed replacement of legacy auth routes.

The oversized legacy API module still contains historical auth handlers. This
composition layer removes every handler registered on the security-sensitive
legacy paths and mounts the audited secure auth router in their place. Production
containers must target this module, not ``main:app``.
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
_SECURE_AUTH_MODULE = "modules.rechnungsverarbeitung.src.api.secure_auth_router"


def _is_replaced_post_route(route: object) -> bool:
    path = getattr(route, "path", None)
    methods = getattr(route, "methods", set()) or set()
    return path in _REPLACED_POST_PATHS and "POST" in methods


def _cut_over_secure_auth_routes() -> None:
    """Remove all legacy sensitive handlers and verify the secure final state.

    The legacy module has accumulated duplicate/changed route registrations over
    time. Treating an exact pre-cutover count as a security invariant makes the
    hardened application unavailable even though every matching legacy route can
    be removed deterministically. The security invariant that matters is the
    post-cutover state: each protected path must be served exactly once and only
    by ``secure_auth_router``.
    """
    app.router.routes[:] = [
        route for route in app.router.routes if not _is_replaced_post_route(route)
    ]

    # Defensive check: no matching legacy route may survive filtering.
    remaining_legacy = [
        route for route in app.router.routes if _is_replaced_post_route(route)
    ]
    if remaining_legacy:
        raise RuntimeError(
            "SECURITY: legacy auth routes survived hardened cutover"
        )

    app.include_router(secure_auth_router, prefix="/api/v1")

    active_secure_routes = [
        route
        for route in app.router.routes
        if isinstance(route, APIRoute)
        and route.path in _REPLACED_POST_PATHS
        and "POST" in route.methods
    ]
    active_counts = Counter(route.path for route in active_secure_routes)
    expected = Counter({path: 1 for path in _REPLACED_POST_PATHS})
    if active_counts != expected:
        raise RuntimeError(
            "SECURITY: secure auth route cutover is incomplete or duplicated"
        )

    unexpected_handlers = [
        route
        for route in active_secure_routes
        if route.endpoint.__module__ != _SECURE_AUTH_MODULE
    ]
    if unexpected_handlers:
        raise RuntimeError(
            "SECURITY: a replaced auth path is not served by secure_auth_router"
        )


_cut_over_secure_auth_routes()
