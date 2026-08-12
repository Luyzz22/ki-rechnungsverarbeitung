"""Production app composition with fail-closed replacement of legacy auth routes.

FastAPI >=0.137 preserves included routers as a route tree instead of flattening
all included ``APIRoute`` objects into ``app.router.routes``. The production
composition therefore verifies effective routes via ``iter_route_contexts()``.

The oversized legacy API module still contains historical auth handlers. Until
those handlers are physically removed from ``main.py``, this module unregisters
only the three security-sensitive legacy routes from the canonical ``v1`` router,
invalidates FastAPI's live included-router cache, mounts the audited secure auth
router, and then verifies the effective final route tree. Production containers
must target this module, not ``main:app``.
"""
from __future__ import annotations

from collections import Counter

from fastapi.routing import iter_route_contexts

from modules.rechnungsverarbeitung.src.api.main import app, v1 as legacy_v1_router
from modules.rechnungsverarbeitung.src.api.secure_auth_router import router as secure_auth_router

_REPLACED_POST_PATHS = frozenset(
    {
        "/api/v1/auth/token",
        "/api/v1/auth/forgot-password",
        "/api/v1/users/invite",
    }
)
_SECURE_POST_PATHS = frozenset(
    {
        *_REPLACED_POST_PATHS,
        "/api/v1/auth/reset-password",
        "/api/v1/auth/accept-invite",
    }
)
_SECURE_AUTH_MODULE = "modules.rechnungsverarbeitung.src.api.secure_auth_router"
_LEGACY_AUTH_MODULE = "modules.rechnungsverarbeitung.src.api.main"


def _route_module(route: object) -> str | None:
    return getattr(getattr(route, "endpoint", None), "__module__", None)


def _is_sensitive_legacy_post_route(route: object) -> bool:
    path = getattr(route, "path", None)
    methods = getattr(route, "methods", set()) or set()
    return (
        path in _REPLACED_POST_PATHS
        and "POST" in methods
        and _route_module(route) == _LEGACY_AUTH_MODULE
    )


def _effective_secure_post_routes() -> list[object]:
    """Return effective sensitive auth routes including nested router prefixes."""
    return [
        route
        for route in iter_route_contexts(app.router.routes)
        if getattr(route, "path", None) in _SECURE_POST_PATHS
        and "POST" in (getattr(route, "methods", set()) or set())
    ]


def _assert_exact_secure_routes(routes: list[object]) -> bool:
    counts = Counter(getattr(route, "path", "") for route in routes)
    expected = Counter({path: 1 for path in _SECURE_POST_PATHS})
    return counts == expected and all(
        _route_module(route) == _SECURE_AUTH_MODULE for route in routes
    )


def _retire_legacy_sensitive_routes() -> None:
    """Remove only the known legacy handlers from the canonical v1 router.

    FastAPI 0.137+ keeps router inclusion live and caches effective route
    candidates by a router version counter. Direct route removal therefore has
    to invalidate that cache explicitly. If the expected invalidation hook is
    unavailable, production startup fails closed instead of risking stale
    legacy routing.
    """
    remaining_routes = [
        route
        for route in legacy_v1_router.routes
        if not _is_sensitive_legacy_post_route(route)
    ]
    removed = len(legacy_v1_router.routes) - len(remaining_routes)

    if removed:
        legacy_v1_router.routes[:] = remaining_routes
        mark_routes_changed = getattr(legacy_v1_router, "_mark_routes_changed", None)
        if not callable(mark_routes_changed):
            raise RuntimeError(
                "SECURITY: FastAPI route-cache invalidation API is unavailable"
            )
        mark_routes_changed()

    surviving_legacy = [
        route
        for route in legacy_v1_router.routes
        if _is_sensitive_legacy_post_route(route)
    ]
    if surviving_legacy:
        raise RuntimeError("SECURITY: legacy auth routes survived hardened cutover")


def _cut_over_secure_auth_routes() -> None:
    """Retire legacy handlers and verify the secure effective route tree."""
    _retire_legacy_sensitive_routes()

    existing_routes = _effective_secure_post_routes()
    if existing_routes:
        # Idempotent re-application is allowed only when the complete secure
        # route set already exists exactly once and no foreign handler shares
        # a sensitive path.
        if _assert_exact_secure_routes(existing_routes):
            return
        raise RuntimeError(
            "SECURITY: secure auth route cutover precondition is ambiguous"
        )

    app.include_router(secure_auth_router, prefix="/api/v1")

    active_secure_routes = _effective_secure_post_routes()
    if not _assert_exact_secure_routes(active_secure_routes):
        raise RuntimeError(
            "SECURITY: secure auth route cutover is incomplete, duplicated, or misrouted"
        )


_cut_over_secure_auth_routes()
