from datetime import datetime
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from app.domain.project import utc_now


class DatasetStatus(StrEnum):
    VALIDATION_FAILED = "validation_failed"
    PENDING_REVIEW = "pending_review"
    ANALYSIS_READY = "analysis_ready"
    NEEDS_REVISION = "needs_revision"
    STALE = "stale"


class QualitySeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class QualityIssue(BaseModel):
    code: str
    severity: QualitySeverity
    message: str
    field_key: str | None = None
    occurrence_count: int = Field(ge=1)
    row_numbers: list[int] = Field(default_factory=list, max_length=20)


class FieldQualitySummary(BaseModel):
    field_key: str
    missing_count: int = Field(ge=0)
    missing_rate: float = Field(ge=0, le=1)
    invalid_count: int = Field(ge=0)
    distinct_count: int = Field(ge=0)


class DataQualityReport(BaseModel):
    row_count: int = Field(ge=0)
    column_count: int = Field(ge=0)
    error_count: int = Field(ge=0)
    warning_count: int = Field(ge=0)
    duplicate_primary_key_count: int = Field(ge=0)
    valid_for_analysis: bool
    issues: list[QualityIssue]
    field_summaries: list[FieldQualitySummary]
    validated_at: datetime = Field(default_factory=utc_now)
    validator_version: str


class DatasetVersion(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    source_contract_id: UUID
    source_contract_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    version: int = Field(ge=1)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str
    byte_size: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    storage_key: str
    status: DatasetStatus
    quality_report: DataQualityReport
    reviewer_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_filename(self) -> "DatasetVersion":
        if Path(self.filename).name != self.filename:
            raise ValueError("Dataset filename must not contain a path")
        return self

    def review(self, request: "DatasetReviewRequest") -> "DatasetVersion":
        if (
            request.status is DatasetStatus.ANALYSIS_READY
            and not self.quality_report.valid_for_analysis
        ):
            raise ValueError("Dataset with validation errors cannot be analysis ready")
        return self.model_copy(
            update={
                "status": request.status,
                "reviewer_note": request.note,
                "reviewed_at": utc_now(),
                "updated_at": utc_now(),
            }
        )

    def mark_stale(self) -> "DatasetVersion":
        return self.model_copy(
            update={"status": DatasetStatus.STALE, "updated_at": utc_now()}
        )


class DatasetReviewRequest(BaseModel):
    status: DatasetStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_review(self) -> "DatasetReviewRequest":
        if self.status not in {
            DatasetStatus.ANALYSIS_READY,
            DatasetStatus.NEEDS_REVISION,
        }:
            raise ValueError("Dataset review must approve or request revision")
        if self.status is DatasetStatus.NEEDS_REVISION and not self.note:
            raise ValueError("A revision request requires a note")
        return self


class DatasetRegistry(BaseModel):
    project_id: UUID
    datasets: list[DatasetVersion] = Field(default_factory=list)
    active_dataset_id: UUID | None = None
    updated_at: datetime = Field(default_factory=utc_now)

    def add(self, dataset: DatasetVersion) -> "DatasetRegistry":
        return self.model_copy(
            update={"datasets": [*self.datasets, dataset], "updated_at": utc_now()}
        )

    def replace(self, dataset: DatasetVersion) -> "DatasetRegistry":
        datasets = [
            dataset if existing.id == dataset.id else existing
            for existing in self.datasets
        ]
        active_id = (
            dataset.id
            if dataset.status is DatasetStatus.ANALYSIS_READY
            else (
                None
                if self.active_dataset_id == dataset.id
                else self.active_dataset_id
            )
        )
        if dataset.status is DatasetStatus.ANALYSIS_READY:
            active_id = dataset.id
        return self.model_copy(
            update={
                "datasets": datasets,
                "active_dataset_id": active_id,
                "updated_at": utc_now(),
            }
        )
