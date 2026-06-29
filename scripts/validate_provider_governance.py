#!/usr/bin/env python3
"""Validate FlowCheck+ production provider governance locally."""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from shared.production_preflight import format_preflight_result, run_production_preflight  # noqa: E402


def main() -> int:
    result = run_production_preflight()
    print(format_preflight_result(result))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
