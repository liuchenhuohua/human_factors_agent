from pathlib import Path
from uuid import UUID


class LocalDatasetStorage:
    """Persist immutable source CSV files under opaque project-scoped keys."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, project_id: UUID, dataset_id: UUID, content: bytes) -> str:
        storage_key = f"{project_id}/{dataset_id}.csv"
        target = self._resolve_key(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)
        return storage_key

    def read(self, storage_key: str) -> bytes:
        return self._resolve_key(storage_key).read_bytes()

    def _resolve_key(self, storage_key: str) -> Path:
        target = (self._root / storage_key).resolve()
        if not target.is_relative_to(self._root):
            raise ValueError("Dataset target escaped the storage root")
        return target
