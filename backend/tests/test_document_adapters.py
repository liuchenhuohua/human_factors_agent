from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from pypdf import PdfWriter

from app.adapters.local_document_storage import LocalDocumentStorage
from app.adapters.pypdf_parser import PypdfTextExtractor
from app.domain.evidence_ports import DocumentParsingError


def test_local_document_storage_uses_opaque_project_scoped_key(tmp_path: Path) -> None:
    storage = LocalDocumentStorage(tmp_path / "uploads")
    project_id = uuid4()
    candidate_id = uuid4()
    content = b"%PDF-1.7 fixture"

    document = storage.save(
        project_id,
        candidate_id,
        "../unsafe name.pdf",
        "application/pdf",
        content,
        page_count=2,
    )

    target = tmp_path / "uploads" / document.storage_key
    assert target.read_bytes() == content
    assert document.filename == "unsafe name.pdf"
    assert document.sha256 == sha256(content).hexdigest()
    assert storage.read(document.storage_key) == content
    storage.delete(document.storage_key)
    assert not target.exists()


def test_pdf_parser_reports_scanned_or_empty_pages(tmp_path: Path) -> None:
    path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    with path.open("wb") as stream:
        writer.write(stream)

    with pytest.raises(DocumentParsingError, match="No selectable text"):
        PypdfTextExtractor().parse(path.read_bytes())
