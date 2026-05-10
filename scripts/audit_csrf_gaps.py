#!/usr/bin/env python3
"""Static CSRF regression guard for the legacy FastAPI app.

This script scans web/app.py for authenticated mutating routes that look like
browser/session JSON, form, or multipart handlers but do not call
_require_csrf_token.
It is intentionally conservative and dependency-free.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "web" / "app.py"
DOCUMENTED_EXCEPTIONS = {
    ("POST", "/api/demo/copilot/query"),
    ("POST", "/api/demo/upload"),
}
ROUTE_RE = re.compile(r'^\s*@app\.(post|put|patch|delete)\(\s*["\']([^"\']+)["\']')
SECTION_RE = re.compile(r"^\s*#\s*(?:[=─-]{3,}|===|---)")
DEF_RE = re.compile(r"^\s*(?:async\s+)?def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
TOP_LEVEL_DEF_RE = re.compile(r"^(?:async\s+)?def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(")


@dataclass(frozen=True)
class RouteBlock:
    method: str
    path: str
    function_name: str
    signature: str
    block: str


def _find_function(lines: list[str], start_index: int) -> tuple[int, str, str]:
    """Return (function_line_index, function_name, signature_text)."""
    for idx in range(start_index + 1, len(lines)):
        match = DEF_RE.match(lines[idx])
        if not match:
            continue

        signature_parts = [lines[idx].strip()]
        cursor = idx
        while cursor + 1 < len(lines) and not lines[cursor].rstrip().endswith(":"):
            cursor += 1
            signature_parts.append(lines[cursor].strip())
        return idx, match.group(1), " ".join(signature_parts)

    return start_index, "<unknown>", ""


def _next_boundary(lines: list[str], function_index: int) -> int:
    for idx in range(function_index + 1, len(lines)):
        if (
            ROUTE_RE.match(lines[idx])
            or SECTION_RE.match(lines[idx])
            or TOP_LEVEL_DEF_RE.match(lines[idx])
        ):
            return idx
    return len(lines)


def scan_routes(app_path: Path = APP_PATH) -> list[RouteBlock]:
    lines = app_path.read_text(encoding="utf-8").splitlines()
    routes: list[RouteBlock] = []

    for idx, line in enumerate(lines):
        route_match = ROUTE_RE.match(line)
        if not route_match:
            continue

        method = route_match.group(1).upper()
        path = route_match.group(2)
        function_index, function_name, signature = _find_function(lines, idx)
        end_index = _next_boundary(lines, function_index)
        block = "\n".join(lines[idx:end_index])

        routes.append(
            RouteBlock(
                method=method,
                path=path,
                function_name=function_name,
                signature=signature,
                block=block,
            )
        )

    return routes


def is_candidate(route: RouteBlock) -> bool:
    has_request = "request: Request" in route.signature
    reads_mutating_payload = (
        "await request.json()" in route.block
        or "Form(" in route.signature
        or "File(" in route.signature
    )
    uses_session_auth = (
        "request.session" in route.block
        or "require_login(request)" in route.block
        or "require_admin(request)" in route.block
    )
    has_csrf = "_require_csrf_token" in route.block
    return has_request and reads_mutating_payload and uses_session_auth and not has_csrf


def main() -> int:
    routes = scan_routes()
    gaps = [route for route in routes if is_candidate(route)]

    documented = [
        route for route in gaps if (route.method, route.path) in DOCUMENTED_EXCEPTIONS
    ]
    failures = [
        route for route in gaps if (route.method, route.path) not in DOCUMENTED_EXCEPTIONS
    ]

    if documented:
        print("Documented CSRF exceptions:")
        for route in documented:
            print(f"- {route.method} {route.path} ({route.function_name})")

    if failures:
        print("Potential CSRF gaps:")
        for route in failures:
            print(f"- {route.method} {route.path} ({route.function_name})")
        return 1

    print("CSRF audit passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
