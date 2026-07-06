from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_INFERENCE_FILES = {
    "web/app.py": "legacy web upload, accounting, copilot, demo routes",
    "api_nexus.py": "Nexus invoice and maintenance API",
    "llm_router.py": "legacy OpenAI/Anthropic invoice extraction",
    "invoice_core.py": "legacy invoice processing and OCR orchestration",
    "ocr_optimizer.py": "local OCR guard",
    "ocr_processor.py": "legacy local OCR guard",
    "auto_accounting.py": "OpenAI account suggestion",
    "category_ai.py": "Anthropic category prediction",
    "duplicate_detection.py": "Anthropic duplicate similarity",
    "enterprise_features.py": "OpenAI CFO analysis",
    "mbr/llm.py": "OpenAI MBR narrative generation",
    "smart_maintenance.py": "Gemini maintenance vision",
    "modules/rechnungsverarbeitung/src/api/main.py": "modular API upload, kontierung, copilot",
    "modules/rechnungsverarbeitung/src/invoices/services/invoice_processing.py": "modular upload AI extraction",
    "modules/rechnungsverarbeitung/src/invoices/services/ai_extraction.py": "Gemini/Claude extraction",
    "modules/rechnungsverarbeitung/src/invoices/services/ai_kontierung.py": "Gemini/Claude kontierung",
    "modules/rechnungsverarbeitung/src/invoices/services/finance_copilot.py": "Gemini/Claude copilot",
    "modules/rechnungsverarbeitung/src/invoices/services/llama_index_service.py": "Gemini RAG indexing/query",
}

NON_INFERENCE_ADAPTERS = {
    "shared/providers/provider_factory.py": "selection only; no SDK client request",
    "shared/provider_governance.py": "policy validation only; no SDK client request",
    "database.py": "persistence only; no provider request",
}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_active_inference_files_use_trusted_organization_context():
    missing = []
    for relative, purpose in ACTIVE_INFERENCE_FILES.items():
        text = _read(relative)
        if (
            "assert_inference_allowed" not in text
            and "process_invoice_upload(" not in text
            and "extract_invoice_data(" not in text
            and "process_maintenance_request_v2(" not in text
        ):
            missing.append(f"{relative}: no inference guard marker ({purpose})")
            continue
        if "organization_context" not in text:
            missing.append(f"{relative}: no organization_context propagation ({purpose})")
        if (
            "assert_organization_inference_allowed" not in text
            and "resolve_trusted_organization_context" not in text
            and "organization_context=organization_context" not in text
        ):
            missing.append(f"{relative}: no trusted organization context guard ({purpose})")

    assert missing == []


def test_provider_factory_does_not_accept_raw_client_organization_or_region():
    text = _read("shared/providers/provider_factory.py")
    signature = text[text.index("def select_provider_for_purpose") : text.index(") -> InferenceProvider:", text.index("def select_provider_for_purpose"))]

    assert "organization_id" not in signature
    assert "cloud_processing_region" not in signature
    assert "policy_source" not in signature
    assert "organization_context" in signature


def test_no_direct_provider_fallback_without_context_in_active_files():
    direct_sdk_markers = ("OpenAI(", "Anthropic(", "genai.Client(", "client.models.generate_content", "messages.create(", "chat.completions.create(")
    missing = []
    for relative in ACTIVE_INFERENCE_FILES:
        text = _read(relative)
        if any(marker in text for marker in direct_sdk_markers):
            if "organization_context" not in text:
                missing.append(relative)

    assert missing == []


def test_non_inference_adapters_are_explicitly_documented():
    for relative in NON_INFERENCE_ADAPTERS:
        assert (ROOT / relative).exists(), relative
