import json

import pytest

from modules.rechnungsverarbeitung.src.api import main as api_main


class _SessionContext:
    def __init__(self, *, fail: bool = False):
        self.fail = fail

    def __enter__(self):
        if self.fail:
            raise RuntimeError("database unavailable")
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *args, **kwargs):
        return None


@pytest.mark.asyncio
async def test_health_returns_200_when_database_ready(monkeypatch):
    monkeypatch.setattr(
        api_main,
        "get_session",
        lambda: _SessionContext(),
    )

    response = await api_main.health()
    payload = json.loads(response.body)

    assert response.status_code == 200
    assert payload["status"] == "healthy"
    assert payload["checks"] == {
        "api": "ok",
        "database": "ok",
    }


@pytest.mark.asyncio
async def test_health_returns_503_when_database_unavailable(monkeypatch):
    monkeypatch.setattr(
        api_main,
        "get_session",
        lambda: _SessionContext(fail=True),
    )

    response = await api_main.health()
    payload = json.loads(response.body)

    assert response.status_code == 503
    assert payload["status"] == "degraded"
    assert payload["checks"] == {
        "api": "ok",
        "database": "error",
    }
