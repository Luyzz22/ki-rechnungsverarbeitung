import ast
import importlib
import re
import sqlite3
import sys
from pathlib import Path

from shared.inference_policy import (
    DataClass,
    InferenceProfile,
    InferenceProvider,
    evaluate_inference_policy,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

EXCLUDED_ACTIVE_SCAN_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".runtime-data",
    "__pycache__",
    "_archive",
    "_archive_20260217_194225",
    "_old_code",
    "backup_2025-11-18",
    "backup_20260203_162219",
    "docs",
    "tests",
    "venv",
}

EXCLUDED_ACTIVE_SCAN_NAMES = {
    "web/app_before_finance_copilot_20251130_025356.py",
    "web/app_before_upload_dev_patch.py",
    "web/app_jobhelper_backup_20251124_021326.py",
    "web/app.py.backup_demo",
    "web/app.py.backup_demo2",
    "web/app.py.backup_kontierung_20260109_122642",
    "web/app.py.backup_stats",
    "web/app.py.backup_unified_20251229_201552",
    "web/app.py.backup_zahlungen_20260109_171610",
}

DIRECT_INFERENCE_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"\bfrom\s+openai\s+import\s+OpenAI\b",
        r"\bfrom\s+anthropic\s+import\s+Anthropic\b",
        r"\bimport\s+anthropic\b",
        r"\bfrom\s+google\s+import\s+genai\b",
        r"\bfrom\s+google\.genai\s+import\b",
        r"\bfrom\s+llama_index\.llms\.gemini\s+import\s+Gemini\b",
        r"\.chat\.completions\.create\(",
        r"\.messages\.create\(",
        r"\.models\.generate_content\(",
        r"\bLLMRouter\.generate_response\(",
        r"\bpytesseract\.image_to_(?:data|string)\(",
        r"\bconvert_from_path\(",
    )
]

PROVIDER_ENDPOINT_PATTERNS = [
    re.compile(pattern)
    for pattern in (
        r"openai\.com",
        r"anthropic\.com",
        r"generativelanguage\.googleapis\.com",
    )
]


def _active_python_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*.py"):
        rel = path.relative_to(REPO_ROOT)
        rel_text = rel.as_posix()
        if any(part in EXCLUDED_ACTIVE_SCAN_PARTS for part in rel.parts):
            continue
        if rel_text in EXCLUDED_ACTIVE_SCAN_NAMES:
            continue
        if ".backup" in rel_text or rel.name.endswith((".bak", ".backup")):
            continue
        files.append(path)
    return sorted(files)


def test_active_direct_inference_files_use_central_guard():
    missing_guard: list[str] = []

    for path in _active_python_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not any(pattern.search(text) for pattern in DIRECT_INFERENCE_PATTERNS):
            continue
        if "assert_inference_allowed" not in text:
            missing_guard.append(path.relative_to(REPO_ROOT).as_posix())

    assert missing_guard == []


def test_no_active_file_hardcodes_direct_provider_endpoint_urls():
    offenders: list[str] = []
    for path in _active_python_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(pattern.search(text) for pattern in PROVIDER_ENDPOINT_PATTERNS):
            offenders.append(path.relative_to(REPO_ROOT).as_posix())

    assert offenders == []


def test_policy_runtime_matrix_professional_and_sovereign():
    professional_denied = [
        InferenceProvider.OPENAI_DIRECT,
        InferenceProvider.ANTHROPIC_DIRECT,
        InferenceProvider.GEMINI_DIRECT,
    ]
    for provider in professional_denied:
        decision = evaluate_inference_policy(
            data_class=DataClass.PROFESSIONAL_SECRET,
            inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
            provider=provider,
            purpose="runtime_matrix",
        )
        assert decision.allowed is False
        assert decision.error_code == "INFERENCE_POLICY_DENIED"

    azure_allowed = evaluate_inference_policy(
        data_class=DataClass.PROFESSIONAL_SECRET,
        inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        provider=InferenceProvider.AZURE_OPENAI_EU,
        purpose="runtime_matrix",
    )
    assert azure_allowed.allowed is True

    azure_unconfigured = evaluate_inference_policy(
        data_class=DataClass.PROFESSIONAL_SECRET,
        inference_profile=InferenceProfile.PROFESSIONAL_SECRECY,
        provider=InferenceProvider.AZURE_OPENAI_EU,
        purpose="runtime_matrix",
        provider_configured=False,
    )
    assert azure_unconfigured.allowed is False
    assert azure_unconfigured.error_code == "INFERENCE_POLICY_DENIED"
    assert InferenceProvider.OPENAI_DIRECT.value not in azure_unconfigured.allowed_providers
    assert InferenceProvider.ANTHROPIC_DIRECT.value not in azure_unconfigured.allowed_providers
    assert InferenceProvider.GEMINI_DIRECT.value not in azure_unconfigured.allowed_providers

    local_allowed = evaluate_inference_policy(
        data_class=DataClass.SOVEREIGN_SECRET,
        inference_profile=InferenceProfile.SOVEREIGN,
        provider=InferenceProvider.LOCAL_OPENAI_COMPAT,
        purpose="runtime_matrix",
    )
    assert local_allowed.allowed is True

    for provider in (
        InferenceProvider.AZURE_OPENAI_EU,
        InferenceProvider.OPENAI_DIRECT,
        InferenceProvider.ANTHROPIC_DIRECT,
        InferenceProvider.GEMINI_DIRECT,
    ):
        decision = evaluate_inference_policy(
            data_class=DataClass.SOVEREIGN_SECRET,
            inference_profile=InferenceProfile.SOVEREIGN,
            provider=provider,
            purpose="runtime_matrix",
        )
        assert decision.allowed is False
        assert decision.error_code == "INFERENCE_POLICY_DENIED"


def test_unknown_policy_inputs_fail_closed():
    cases = [
        {"data_class": "unknown", "inference_profile": InferenceProfile.STANDARD, "provider": InferenceProvider.OPENAI_DIRECT},
        {"data_class": DataClass.INVOICE_CONFIDENTIAL, "inference_profile": "unknown", "provider": InferenceProvider.OPENAI_DIRECT},
        {"data_class": DataClass.INVOICE_CONFIDENTIAL, "inference_profile": InferenceProfile.STANDARD, "provider": "unknown"},
    ]
    for case in cases:
        decision = evaluate_inference_policy(**case, purpose="unknown_inputs")
        assert decision.allowed is False
        assert decision.error_code == "INFERENCE_POLICY_DENIED"


def test_api_request_models_do_not_accept_policy_control_fields():
    forbidden_fields = {
        "data_class",
        "inference_profile",
        "provider",
        "provider_selected",
        "allowed_providers",
        "policy_version",
        "policy_decision",
    }
    checked_files = [
        REPO_ROOT / "api_nexus.py",
        REPO_ROOT / "web/app.py",
        REPO_ROOT / "modules/rechnungsverarbeitung/src/api/main.py",
    ]

    offenders: list[str] = []
    for path in checked_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if "Request" not in node.name:
                continue
            fields = {
                stmt.target.id
                for stmt in node.body
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)
            }
            fields.update(
                target.id
                for stmt in node.body
                if isinstance(stmt, ast.Assign)
                for target in stmt.targets
                if isinstance(target, ast.Name)
            )
            forbidden_present = sorted(fields & forbidden_fields)
            if forbidden_present:
                offenders.append(f"{path.relative_to(REPO_ROOT).as_posix()}::{node.name}:{forbidden_present}")

    assert offenders == []


def _reload_database_for_path(monkeypatch, db_path: Path):
    monkeypatch.setenv("INVOICE_DB_PATH", str(db_path))
    sys.modules.pop("database", None)
    return importlib.import_module("database")


def test_fresh_sqlite_db_gets_policy_metadata(monkeypatch, tmp_path):
    database = _reload_database_for_path(monkeypatch, tmp_path / "fresh.sqlite")

    database.save_job(
        "job-fresh",
        {
            "status": "completed",
            "total": 1,
            "successful": 1,
            "stats": {"total_netto": 10, "total_mwst": 1.9, "average_brutto": 11.9},
            "total_amount": 11.9,
        },
        user_id=1,
    )
    database.save_invoices(
        "job-fresh",
        [
            {
                "rechnungsnummer": "RE-1",
                "rechnungsaussteller": "Test GmbH",
                "betrag_brutto": 11.9,
                "data_class": "invoice_confidential",
                "inference_profile": "standard",
                "provider_selected": "openai_direct",
                "policy_decision": "allowed",
            }
        ],
    )

    rows = database.get_invoices_by_job("job-fresh")
    assert len(rows) == 1
    assert rows[0]["data_class"] == "invoice_confidential"
    assert rows[0]["inference_profile"] == "standard"
    assert rows[0]["provider_selected"] == "openai_direct"
    assert rows[0]["policy_decision"] == "allowed"


def test_old_sqlite_db_is_migrated_without_destroying_rows(monkeypatch, tmp_path):
    db_path = tmp_path / "old.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            created_at TEXT,
            status TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT,
            rechnungsnummer TEXT,
            betrag_brutto REAL
        )
        """
    )
    conn.execute("INSERT INTO jobs (job_id, created_at, status) VALUES (?, ?, ?)", ("old-job", "2026-01-01", "completed"))
    conn.execute(
        "INSERT INTO invoices (job_id, rechnungsnummer, betrag_brutto) VALUES (?, ?, ?)",
        ("old-job", "ALT-1", 12.3),
    )
    conn.commit()
    conn.close()

    _reload_database_for_path(monkeypatch, db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    invoice_columns = {row["name"] for row in conn.execute("PRAGMA table_info(invoices)").fetchall()}
    job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
    row = conn.execute("SELECT * FROM invoices WHERE job_id = ?", ("old-job",)).fetchone()
    conn.close()

    assert row is not None
    assert row["rechnungsnummer"] == "ALT-1"
    assert {"data_class", "inference_profile", "provider_selected", "policy_version", "policy_decision"} <= invoice_columns
    assert {"data_class", "inference_profile", "provider_selected", "policy_version", "policy_decision"} <= job_columns
