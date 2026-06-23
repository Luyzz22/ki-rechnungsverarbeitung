"""End-to-End Smoke-Test der wichtigsten Routen (Onboarding-Flow).

Registriert einen Nutzer, meldet ihn an und prüft, dass die zentralen Seiten
und Alias-Pfade nicht mit Server-Fehlern (5xx) oder fehlenden Routen (404)
antworten. Wird übersprungen, wenn die App-Abhängigkeiten fehlen.
"""

import os
import re
import tempfile

import pytest

# Env VOR dem Import von web.app setzen (Session-Secret + isolierte Test-DB)
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ["INVOICE_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "routes_smoke.db")

web_app = pytest.importorskip("web.app", reason="App-Abhängigkeiten nicht installiert")
fastapi_testclient = pytest.importorskip("fastapi.testclient")

from pathlib import Path  # noqa: E402

_DB_FILE = Path(os.environ["INVOICE_DB_PATH"])


@pytest.fixture(autouse=True)
def _pin_db():
    """DB-Pfad-Resolver vor JEDEM Test fixieren (verhindert Leaks durch andere
    Test-Module, die _ensure_db_path global überschreiben)."""
    import database
    database._ensure_db_path = lambda: _DB_FILE
    yield


@pytest.fixture(scope="module")
def client():
    # DB-Pfad deterministisch fixieren (unabhängig von Import-Reihenfolge), da
    # get_connection() den Pfad zur Laufzeit über _ensure_db_path() auflöst.
    import database
    _DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    database._ensure_db_path = lambda: _DB_FILE

    from database import init_database, init_users_table
    init_database()
    init_users_table()
    try:
        import rbac
        rbac.init_rbac_tables()
    except Exception:
        pass
    c = fastapi_testclient.TestClient(
        web_app.app, base_url="https://app.sbsdeutschland.com", raise_server_exceptions=False
    )

    def _csrf(html):
        m = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)', html)
        return m.group(1) if m else None

    r = c.get("/register")
    c.post("/register", data={"name": "T", "email": "smoke@test.de", "company": "ACME",
            "password": "Test1234", "password2": "Test1234", "csrf_token": _csrf(r.text)},
            follow_redirects=False)
    r = c.get("/login")
    c.post("/login", data={"email": "smoke@test.de", "password": "Test1234",
            "csrf_token": _csrf(r.text)}, follow_redirects=False)
    return c


# Seiten, die mit 200 rendern müssen
PAGES_200 = [
    "/login", "/register", "/password-reset/request",
    "/dashboard", "/dashboard/enterprise", "/history", "/freigaben",
    "/exports", "/lieferanten", "/audit", "/verfahrensdokumentation",
    "/gobd/export-protokoll", "/landing", "/sicherheit", "/compliance",
    "/avv", "/api", "/preise", "/pricing", "/profile", "/settings",
    "/approvals", "/zahlungen", "/budget", "/mbr", "/health",
]

# Alias-Pfade, die sinnvoll weiterleiten (3xx) müssen
ALIASES_REDIRECT = ["/upload", "/rechnungen", "/export"]


@pytest.mark.parametrize("path", PAGES_200)
def test_page_renders(client, path):
    r = client.get(path, follow_redirects=False)
    assert r.status_code < 400, f"{path} -> {r.status_code}"


@pytest.mark.parametrize("path", ALIASES_REDIRECT)
def test_alias_redirects(client, path):
    r = client.get(path, follow_redirects=False)
    assert r.status_code in (301, 302, 303, 307, 308), f"{path} -> {r.status_code}"


def test_no_route_is_missing(client):
    """Keine der Kernrouten darf 404 liefern."""
    for path in PAGES_200 + ALIASES_REDIRECT:
        r = client.get(path, follow_redirects=False)
        assert r.status_code != 404, f"{path} fehlt (404)"
