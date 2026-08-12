from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hardened_app_does_not_apply_legacy_numeric_schema_guard():
    """The modular production auth stack currently uses string/UUID identities.

    Until the dual identity contracts are consolidated, the legacy INTEGER/SERIAL
    guard must remain scoped to the SQLite→PostgreSQL legacy migration path and
    must not reject a valid modular users.id TEXT/VARCHAR schema at app startup.
    """
    text = (ROOT / "modules/rechnungsverarbeitung/src/api/hardened_app.py").read_text(
        encoding="utf-8"
    )
    assert "validate_configured_postgres_schema" not in text


def test_migration_script_validates_target_before_schema_or_data_writes():
    text = (ROOT / "scripts/migrate_sqlite_to_postgres.py").read_text(encoding="utf-8")
    guard_call = text.index("assessment = validate_postgres_schema(pg)")
    schema_write = text.index("with pg.cursor() as cur:", guard_call)
    assert guard_call < schema_write
    assert "except PostgresSchemaCompatibilityError" in text


def test_assessment_script_is_explicitly_read_only_and_aggregate_only():
    text = (ROOT / "scripts/assess_postgres_id_migration.py").read_text(encoding="utf-8")
    assert "SET TRANSACTION READ ONLY" in text
    assert "SELECT COUNT(*)" in text
    assert "automatic_migration_permitted\": False" in text
    assert "SELECT * FROM users" not in text
