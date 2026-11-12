import hashlib
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.evidence import EvidenceDocument


class LocalDocumentStorage:
    """Persist uploaded research documents under an opaque, project-scoped key."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        project_id: UUID,
        candidate_id: UUID,
        filename: str,
        content_type: str,
        content: bytes,
        page_count: int,
    ) -> EvidenceDocument:
        document_id = uuid4()
        storage_key = f"{project_id}/{candidate_id}/{document_id}.pdf"
        target = (self._root / storage_key).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError("Document target escaped the storage root")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return EvidenceDocument(
            id=document_id,
            candidate_id=candidate_id,
            filename=Path(filename).name,
            content_type=content_type,
            byte_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            storage_key=storage_key,
            page_count=page_count,
        )

    def read(self, storage_key: str) -> bytes:
        target = self._resolve_key(storage_key)
        return target.read_bytes()

    def delete(self, storage_key: str) -> None:
        self._resolve_key(storage_key).unlink(missing_ok=True)

    def _resolve_key(self, storage_key: str) -> Path:
        target = (self._root / storage_key).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError("Document target escaped the storage root")
        return target
