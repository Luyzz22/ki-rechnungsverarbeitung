from pathlib import Path

import pytest

from modules.rechnungsverarbeitung.src.invoices.services.file_storage import (
    FileStorageService,
    UnsafeStoragePathError,
)


def test_store_and_retrieve_stays_inside_tenant_document_directory(tmp_path):
    service = FileStorageService(root=tmp_path / "storage")

    stored = Path(service.store("tenant-1", "doc-1", "Rechnung ÄÖ 2026.pdf", b"pdf"))

    assert stored == (tmp_path / "storage" / "tenant-1" / "doc-1" / "Rechnung ÄÖ 2026.pdf").resolve()
    assert service.retrieve("tenant-1", "doc-1", "Rechnung ÄÖ 2026.pdf") == b"pdf"
    assert service.get_path("tenant-1", "doc-1", "Rechnung ÄÖ 2026.pdf") == stored


@pytest.mark.parametrize(
    "file_name",
    [
        "../outside.pdf",
        "../../outside.pdf",
        "/tmp/outside.pdf",
        r"..\outside.pdf",
        ".",
        "..",
        "bad\x00name.pdf",
    ],
)
def test_store_rejects_unsafe_user_controlled_file_names(tmp_path, file_name):
    service = FileStorageService(root=tmp_path / "storage")

    with pytest.raises(UnsafeStoragePathError):
        service.store("tenant-1", "doc-1", file_name, b"sensitive")

    assert not (tmp_path / "outside.pdf").exists()


@pytest.mark.parametrize("tenant_id", ["../other", "/tmp/other", r"..\other", ".", ".."])
def test_tenant_component_cannot_escape_storage_root(tmp_path, tenant_id):
    service = FileStorageService(root=tmp_path / "storage")

    with pytest.raises(UnsafeStoragePathError):
        service.store(tenant_id, "doc-1", "invoice.pdf", b"sensitive")


@pytest.mark.parametrize("document_id", ["../other", "/tmp/other", r"..\other", ".", ".."])
def test_document_component_cannot_escape_tenant_directory(tmp_path, document_id):
    service = FileStorageService(root=tmp_path / "storage")

    with pytest.raises(UnsafeStoragePathError):
        service.store("tenant-1", document_id, "invoice.pdf", b"sensitive")


def test_get_path_and_retrieve_reject_traversal_instead_of_reading_arbitrary_file(tmp_path):
    service = FileStorageService(root=tmp_path / "storage")
    secret = tmp_path / "secret.txt"
    secret.write_text("do-not-read")

    with pytest.raises(UnsafeStoragePathError):
        service.get_path("tenant-1", "doc-1", "../../../secret.txt")
    with pytest.raises(UnsafeStoragePathError):
        service.retrieve("tenant-1", "doc-1", "../../../secret.txt")


def test_preexisting_symlink_escape_is_rejected(tmp_path):
    root = tmp_path / "storage"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "tenant-1").symlink_to(outside, target_is_directory=True)

    service = FileStorageService(root=root)

    with pytest.raises(UnsafeStoragePathError):
        service.store("tenant-1", "doc-1", "invoice.pdf", b"sensitive")

    assert not (outside / "doc-1" / "invoice.pdf").exists()
