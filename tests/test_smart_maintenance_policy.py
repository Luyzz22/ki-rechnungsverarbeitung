import asyncio
from unittest.mock import AsyncMock, Mock

import smart_maintenance
from shared.inference_policy import DataClass, InferenceProfile
from shared.organization_context import TrustedOrganizationContext


def test_hydraulikdoc_policy_denial_prevents_analyzer_construction(monkeypatch):
    constructor = Mock()
    monkeypatch.setattr(smart_maintenance, "get_hydraulikdoc_analyzer", constructor)
    monkeypatch.setattr(
        "shared.organization_context.is_production_runtime",
        lambda **_kwargs: True,
    )

    result = asyncio.run(
        smart_maintenance.analyze_part_with_hydraulikdoc(
            "not-decoded-before-policy",
            organization_context=None,
        )
    )

    assert result["error"] == "ORG_CONTEXT_REQUIRED"
    constructor.assert_not_called()


def test_hydraulikdoc_failure_fallback_preserves_trusted_context(monkeypatch):
    context = TrustedOrganizationContext(
        organization_id=10,
        tenant_id="1",
        user_id=1,
        source="invoice_owner",
    )
    fallback = AsyncMock(return_value={"part_number": None})
    monkeypatch.setattr(
        smart_maintenance,
        "assert_organization_inference_allowed",
        lambda **_kwargs: InferenceProfile.STANDARD,
    )
    monkeypatch.setattr(
        smart_maintenance,
        "assert_inference_allowed",
        lambda **_kwargs: Mock(),
    )
    monkeypatch.setattr(
        smart_maintenance,
        "get_hydraulikdoc_analyzer",
        Mock(side_effect=RuntimeError("controlled failure")),
    )
    monkeypatch.setattr(smart_maintenance, "recognize_part_from_image", fallback)

    result = asyncio.run(
        smart_maintenance.analyze_part_with_hydraulikdoc(
            "not-decoded",
            data_class=DataClass.INTERNAL.value,
            inference_profile=InferenceProfile.STANDARD.value,
            organization_context=context,
        )
    )

    assert result == {"part_number": None}
    fallback.assert_awaited_once_with(
        "not-decoded",
        "",
        data_class=DataClass.INTERNAL.value,
        inference_profile=InferenceProfile.STANDARD.value,
        organization_context=context,
    )
