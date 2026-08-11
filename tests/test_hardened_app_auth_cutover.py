from pathlib import Path

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from modules.rechnungsverarbeitung.src.api import hardened_app
from modules.rechnungsverarbeitung.src.api import secure_auth_router as secure


_SECURE_MODULE = "modules.rechnungsverarbeitung.src.api.secure_auth_router"
_REPLACED_POST_PATHS = {
    "/api/v1/auth/token",
    "/api/v1/auth/forgot-password",
    "/api/v1/users/invite",
}


def _post_routes(path: str) -> list[APIRoute]:
    return [
        route
        for route in hardened_app.app.router.routes
        if isinstance(route, APIRoute)
        and route.path == path
        and "POST" in route.methods
    ]


def test_replaced_auth_paths_have_exactly_one_secure_handler():
    for path in _REPLACED_POST_PATHS:
        routes = _post_routes(path)
        assert len(routes) == 1, path
        assert routes[0].endpoint.__module__ == _SECURE_MODULE


def test_password_action_endpoints_are_exposed_once_by_secure_router():
    for path in (
        "/api/v1/auth/reset-password",
        "/api/v1/auth/accept-invite",
    ):
        routes = _post_routes(path)
        assert len(routes) == 1, path
        assert routes[0].endpoint.__module__ == _SECURE_MODULE


def test_retired_demo_credentials_are_not_served_by_active_login(monkeypatch):
    def reject_login(**_kwargs):
        raise ValueError("invalid")

    monkeypatch.setattr(secure._user_service, "login", reject_login)
    client = TestClient(hardened_app.app)

    response = client.post(
        "/api/v1/auth/token",
        json={"email": "demo@sbsdeutschland.de", "password": "demo2026"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}


def test_hardened_cutover_can_be_reapplied_without_duplicate_sensitive_routes():
    hardened_app._cut_over_secure_auth_routes()

    for path in _REPLACED_POST_PATHS:
        routes = _post_routes(path)
        assert len(routes) == 1, path
        assert routes[0].endpoint.__module__ == _SECURE_MODULE


def test_production_dockerfile_targets_hardened_app():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "modules.rechnungsverarbeitung.src.api.hardened_app:app" in dockerfile
    assert "modules.rechnungsverarbeitung.src.api.main:app" not in dockerfile
