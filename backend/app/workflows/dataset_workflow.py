import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.dataset import (
    DatasetRegistry,
    DatasetReviewRequest,
    DatasetStatus,
    DatasetVersion,
)
from app.domain.dataset_ports import (
    DatasetStorage,
    DatasetStore,
    DatasetValidationError,
    DatasetValidator,
)
from app.domain.preparation import DataContract, DataContractContent, PreparationStatus
from app.domain.project import utc_now
from app.workflows.preparation_workflow import PreparationWorkflow


class DatasetWorkflow:
    """Own immutable uploads, contract validation, review, and invalidation."""

    allowed_content_types = {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "application/octet-stream",
        "",
    }

    def __init__(
        self,
        validator: DatasetValidator,
        storage: DatasetStorage,
        store: DatasetStore,
        preparation_workflow: PreparationWorkflow,
        max_upload_bytes: int,
    ) -> None:
        self._validator = validator
        self._storage = storage
        self._store = store
        self._preparation_workflow = preparation_workflow
        self.max_upload_bytes = max_upload_bytes

    def upload(
        self,
        project_id: UUID,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> DatasetRegistry:
        contract = self._require_approved_contract(project_id)
        clean_filename = Path(filename).name
        normalized_content_type = (content_type or "").split(";", 1)[0].lower()
        if not clean_filename.lower().endswith(".csv"):
            raise DatasetValidationError("Only CSV files are accepted")
        if normalized_content_type not in self.allowed_content_types:
            raise DatasetValidationError("Uploaded file must use a CSV content type")
        if not content:
            raise DatasetValidationError("CSV file is empty")
        if len(content) > self.max_upload_bytes:
            raise DatasetValidationError(
                f"CSV exceeds the {self.max_upload_bytes // (1024 * 1024)} MB limit"
            )

        report = self._validator.validate(content, contract)
        registry = self._store.get(project_id) or DatasetRegistry(project_id=project_id)
        dataset_id = uuid4()
        storage_key = self._storage.save(project_id, dataset_id, content)
        dataset = DatasetVersion(
            id=dataset_id,
            project_id=project_id,
            source_contract_id=contract.id,
            source_contract_hash=self._contract_hash(contract),
            version=max((item.version for item in registry.datasets), default=0) + 1,
            filename=clean_filename,
            content_type=normalized_content_type or "text/csv",
            byte_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            storage_key=storage_key,
            status=(
                DatasetStatus.PENDING_REVIEW
                if report.valid_for_analysis
                else DatasetStatus.VALIDATION_FAILED
            ),
            quality_report=report,
        )
        registry = registry.add(dataset)
        self._store.save(registry)
        return registry

    def get(self, project_id: UUID) -> DatasetRegistry | None:
        registry = self._store.get(project_id)
        if registry is None:
            return None
        preparation = self._preparation_workflow.get(project_id)
        contract = preparation.data_contract if preparation is not None else None
        current_hash = (
            self._contract_hash(contract)
            if contract is not None and contract.status is PreparationStatus.APPROVED
            else None
        )
        changed = False
        datasets: list[DatasetVersion] = []
        for dataset in registry.datasets:
            is_current = (
                contract is not None
                and dataset.source_contract_id == contract.id
                and dataset.source_contract_hash == current_hash
            )
            if not is_current and dataset.status is not DatasetStatus.STALE:
                dataset = dataset.mark_stale()
                changed = True
            datasets.append(dataset)
        active_id = registry.active_dataset_id
        if active_id is not None and any(
            item.id == active_id and item.status is DatasetStatus.STALE
            for item in datasets
        ):
            active_id = None
            changed = True
        if changed:
            registry = registry.model_copy(
                update={
                    "datasets": datasets,
                    "active_dataset_id": active_id,
                    "updated_at": utc_now(),
                }
            )
            self._store.save(registry)
        return registry

    def review(
        self,
        project_id: UUID,
        dataset_id: UUID,
        request: DatasetReviewRequest,
    ) -> DatasetRegistry:
        contract = self._require_approved_contract(project_id)
        registry = self.get(project_id)
        if registry is None:
            raise KeyError(f"Datasets for project {project_id} not found")
        dataset = next(
            (item for item in registry.datasets if item.id == dataset_id),
            None,
        )
        if dataset is None:
            raise KeyError(f"Dataset {dataset_id} not found")
        if dataset.status is DatasetStatus.STALE:
            raise ValueError("Dataset contract changed; upload a new version")
        if (
            dataset.source_contract_id != contract.id
            or dataset.source_contract_hash != self._contract_hash(contract)
        ):
            raise ValueError("Dataset contract changed; upload a new version")
        registry = registry.replace(dataset.review(request))
        self._store.save(registry)
        return registry

    def download(self, project_id: UUID, dataset_id: UUID) -> tuple[DatasetVersion, bytes]:
        registry = self._store.get(project_id)
        if registry is None:
            raise KeyError(f"Datasets for project {project_id} not found")
        dataset = next(
            (item for item in registry.datasets if item.id == dataset_id),
            None,
        )
        if dataset is None:
            raise KeyError(f"Dataset {dataset_id} not found")
        return dataset, self._storage.read(dataset.storage_key)

    def _require_approved_contract(self, project_id: UUID) -> DataContract:
        preparation = self._preparation_workflow.get(project_id)
        if preparation is None or preparation.data_contract is None:
            raise KeyError("Data contract not found")
        contract = preparation.data_contract
        if contract.status is not PreparationStatus.APPROVED:
            raise ValueError("Data contract must be approved before uploading data")
        return contract

    @staticmethod
    def _contract_hash(contract: DataContract) -> str:
        content = DataContractContent.model_validate(
            contract.model_dump(include=set(DataContractContent.model_fields))
        )
        canonical = json.dumps(
            content.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
