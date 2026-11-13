from typing import Protocol
from uuid import UUID

from app.domain.dataset import DataQualityReport, DatasetRegistry
from app.domain.preparation import DataContract


class DatasetValidationError(ValueError):
    pass


class DatasetValidator(Protocol):
    def validate(self, content: bytes, contract: DataContract) -> DataQualityReport: ...


class DatasetStorage(Protocol):
    def save(self, project_id: UUID, dataset_id: UUID, content: bytes) -> str: ...

    def read(self, storage_key: str) -> bytes: ...


class DatasetStore(Protocol):
    def save(self, registry: DatasetRegistry) -> None: ...

    def get(self, project_id: UUID) -> DatasetRegistry | None: ...
