"""Production app composition with fail-closed security cutovers.

FastAPI >=0.137 preserves included routers as a route tree instead of flattening
all included ``APIRoute`` objects into ``app.router.routes``. The production
composition therefore verifies effective routes via ``iter_route_contexts()``.

The oversized legacy API module still contains historical auth handlers and a
few transitional audit-identity call shapes. Until those are physically removed
from ``main.py``, this module performs explicit production cutovers:

1. unregister the three security-sensitive legacy auth routes and mount the
   audited secure auth router;
2. unregister upload/batch/transition routes whose legacy call shapes accept or
   persist client-controlled audit attribution, then mount the authenticated
   audit router;
3. install compatibility hardening for remaining legacy service calls so
   technical actors stay distinguishable while human/service attribution comes
   from the authenticated principal.

Production containers must target this module, not ``main:app``.
"""
from __future__ import annotations

from collections import Counter

from fastapi.routing import iter_route_contexts

from modules.rechnungsverarbeitung.src.api import main as legacy_api
from modules.rechnungsverarbeitung.src.api.audit_actor_hardening import (
    install_audit_actor_hardening,
)
from modules.rechnungsverarbeitung.src.api.main import app, v1 as legacy_v1_router
from modules.rechnungsverarbeitung.src.api.secure_audit_router import (
    router as secure_audit_router,
)
from modules.rechnungsverarbeitung.src.api.secure_auth_router import router as secure_auth_router

_AUTH_REPLACED_POST_PATHS = frozenset(
    {
        "/api/v1/auth/token",
        "/api/v1/auth/forgot-password",
        "/api/v1/users/invite",
    }
)
_SECURE_AUTH_POST_PATHS = frozenset(
    {
        *_AUTH_REPLACED_POST_PATHS,
        "/api/v1/auth/reset-password",
        "/api/v1/auth/accept-invite",
    }
)
_AUDIT_REPLACED_POST_PATHS = frozenset(
    {
        "/api/v1/invoices/upload",
        "/api/v1/invoices/upload-batch",
        "/api/v1/invoices/{document_id}/transition",
    }
)
_SECURE_AUTH_MODULE = "modules.rechnungsverarbeitung.src.api.secure_auth_router"
_SECURE_AUDIT_MODULE = "modules.rechnungsverarbeitung.src.api.secure_audit_router"
_LEGACY_API_MODULE = "modules.rechnungsverarbeitung.src.api.main"


def _route_module(route: object) -> str | None:
    return getattr(getattr(route, "endpoint", None), "__module__", None)


def _is_legacy_post_route(route: object, paths: frozenset[str]) -> bool:
    path = getattr(route, "path", None)
    methods = getattr(route, "methods", set()) or set()
    return path in paths and "POST" in methods and _route_module(route) == _LEGACY_API_MODULE


def _effective_post_routes(paths: frozenset[str]) -> list[object]:
    return [
        route
        for route in iter_route_contexts(app.router.routes)
        if getattr(route, "path", None) in paths
        and "POST" in (getattr(route, "methods", set()) or set())
    ]


def _assert_exact_routes(
    routes: list[object],
    *,
    paths: frozenset[str],
    expected_module: str,
) -> bool:
    counts = Counter(getattr(route, "path", "") for route in routes)
    expected = Counter({path: 1 for path in paths})
    return counts == expected and all(_route_module(route) == expected_module for route in routes)


def _retire_legacy_post_routes(paths: frozenset[str], *, label: str) -> None:
    """Remove only an explicit allowlist of legacy POST handlers.

    FastAPI 0.137+ keeps router inclusion live and caches effective route
    candidates by a router version counter. Direct route removal therefore has
    to invalidate that cache explicitly. If the expected invalidation hook is
    unavailable, production startup fails closed instead of risking stale
    legacy routing.
    """
    remaining_routes = [
        route
        for route in legacy_v1_router.routes
        if not _is_legacy_post_route(route, paths)
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
        if _is_legacy_post_route(route, paths)
    ]
    if surviving_legacy:
        raise RuntimeError(f"SECURITY: legacy {label} routes survived hardened cutover")


def _cut_over_secure_auth_routes() -> None:
    """Retire legacy auth handlers and verify the secure effective route tree."""
    _retire_legacy_post_routes(_AUTH_REPLACED_POST_PATHS, label="auth")

    existing_routes = _effective_post_routes(_SECURE_AUTH_POST_PATHS)
    if existing_routes:
        if _assert_exact_routes(
            existing_routes,
            paths=_SECURE_AUTH_POST_PATHS,
            expected_module=_SECURE_AUTH_MODULE,
        ):
            return
        raise RuntimeError("SECURITY: secure auth route cutover precondition is ambiguous")

    app.include_router(secure_auth_router, prefix="/api/v1")

    active_routes = _effective_post_routes(_SECURE_AUTH_POST_PATHS)
    if not _assert_exact_routes(
        active_routes,
        paths=_SECURE_AUTH_POST_PATHS,
        expected_module=_SECURE_AUTH_MODULE,
    ):
        raise RuntimeError(
            "SECURITY: secure auth route cutover is incomplete, duplicated, or misrouted"
        )


def _cut_over_secure_audit_routes() -> None:
    """Replace client-spoofable audit attribution with authenticated routes."""
    _retire_legacy_post_routes(_AUDIT_REPLACED_POST_PATHS, label="audit-identity")

    existing_routes = _effective_post_routes(_AUDIT_REPLACED_POST_PATHS)
    if existing_routes:
        if _assert_exact_routes(
            existing_routes,
            paths=_AUDIT_REPLACED_POST_PATHS,
            expected_module=_SECURE_AUDIT_MODULE,
        ):
            return
        raise RuntimeError(
            "SECURITY: secure audit route cutover precondition is ambiguous"
        )

    app.include_router(secure_audit_router, prefix="/api/v1")

    active_routes = _effective_post_routes(_AUDIT_REPLACED_POST_PATHS)
    if not _assert_exact_routes(
        active_routes,
        paths=_AUDIT_REPLACED_POST_PATHS,
        expected_module=_SECURE_AUDIT_MODULE,
    ):
        raise RuntimeError(
            "SECURITY: secure audit route cutover is incomplete, duplicated, or misrouted"
        )


_cut_over_secure_auth_routes()
install_audit_actor_hardening(legacy_api)
_cut_over_secure_audit_routes()
