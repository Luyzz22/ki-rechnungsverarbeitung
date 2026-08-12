from email.message import EmailMessage

import pytest

from modules.rechnungsverarbeitung.src.invoices.services import email_ingestion
from modules.rechnungsverarbeitung.src.invoices.services.email_ingestion import (
    EmailIngestionService,
    UnmappedEmailSenderError,
)


class _Result:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _Session:
    def __init__(self, row):
        self._row = row

    def execute(self, *args, **kwargs):
        return _Result(self._row)


class _SessionContext:
    def __init__(self, row):
        self._session = _Session(row)

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeImapClient:
    def __init__(self):
        self.created_folders = []
        self.moves = []

    def create_folder(self, folder):
        self.created_folders.append(folder)

    def move(self, uids, folder):
        self.moves.append((uids, folder))


def test_resolve_tenant_returns_only_explicit_mapping(monkeypatch):
    monkeypatch.setattr(
        email_ingestion,
        "get_session",
        lambda: _SessionContext(("tenant-explicit",)),
    )

    service = EmailIngestionService()

    assert service._resolve_tenant("Sender <known@example.com>") == "tenant-explicit"


def test_resolve_tenant_unknown_sender_fails_closed(monkeypatch):
    monkeypatch.setattr(
        email_ingestion,
        "get_session",
        lambda: _SessionContext(None),
    )

    service = EmailIngestionService()

    with pytest.raises(UnmappedEmailSenderError) as exc_info:
        service._resolve_tenant("unknown@example.com")

    assert str(exc_info.value) == "sender_tenant_mapping_missing"


def test_resolve_tenant_missing_address_fails_closed():
    service = EmailIngestionService()

    with pytest.raises(UnmappedEmailSenderError) as exc_info:
        service._resolve_tenant("not-an-email-address")

    assert str(exc_info.value) == "sender_address_missing"


def test_unmapped_message_is_quarantined_before_attachment_persistence(monkeypatch, tmp_path):
    service = EmailIngestionService()
    service.upload_dir = str(tmp_path)
    service.quarantine_folder = "Quarantine"

    monkeypatch.setattr(
        service,
        "_resolve_tenant",
        lambda sender: (_ for _ in ()).throw(
            UnmappedEmailSenderError("sender_tenant_mapping_missing")
        ),
    )

    invoice_record_called = False

    def _unexpected_invoice_record(**kwargs):
        nonlocal invoice_record_called
        invoice_record_called = True

    monkeypatch.setattr(service, "_create_invoice_record", _unexpected_invoice_record)

    message = EmailMessage()
    message["From"] = "unknown@example.com"
    message["To"] = "invoices@example.test"
    message["Subject"] = "Invoice"
    message.set_content("Invoice attached")
    message.add_attachment(
        b"%PDF-1.7 synthetic test payload",
        maintype="application",
        subtype="pdf",
        filename="invoice.pdf",
    )

    client = _FakeImapClient()
    result = service._process_message(
        123,
        {b"RFC822": message.as_bytes()},
        client,
    )

    assert result == []
    assert invoice_record_called is False
    assert list(tmp_path.iterdir()) == []
    assert client.moves == [([123], "Quarantine")]
