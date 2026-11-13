from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.experiment import VariableRole
from app.domain.project import GenerationMetadata, utc_now


class PreparationStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    STALE = "stale"


class PowerTestType(StrEnum):
    INDEPENDENT_T = "independent_t"
    PAIRED_T = "paired_t"
    ONE_WAY_ANOVA = "one_way_anova"
    CORRELATION = "correlation"


class TestAlternative(StrEnum):
    TWO_SIDED = "two-sided"
    LARGER = "larger"
    SMALLER = "smaller"


class PowerAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_type: PowerTestType
    effect_size: float = Field(gt=0)
    alpha: float = Field(gt=0, lt=1)
    target_power: float = Field(gt=0, lt=1)
    alternative: TestAlternative = TestAlternative.TWO_SIDED
    groups: int = Field(default=2, ge=2, le=12)
    allocation_ratio: float = Field(default=1.0, gt=0, le=10)
    attrition_rate: float = Field(default=0.0, ge=0, lt=1)
    sensitivity_effect_sizes: list[float] = Field(default_factory=list, max_length=8)
    sensitivity_powers: list[float] = Field(default_factory=list, max_length=6)

    @model_validator(mode="after")
    def validate_test_inputs(self) -> "PowerAnalysisRequest":
        if self.test_type is PowerTestType.CORRELATION:
            if self.effect_size >= 1:
                raise ValueError("Correlation effect size must be less than one")
            if any(value >= 1 for value in self.sensitivity_effect_sizes):
                raise ValueError("Correlation sensitivity effects must be less than one")
        if self.test_type is PowerTestType.INDEPENDENT_T and self.groups != 2:
            raise ValueError("Independent t-test requires exactly two groups")
        if self.test_type is PowerTestType.ONE_WAY_ANOVA:
            if self.alternative is not TestAlternative.TWO_SIDED:
                raise ValueError("One-way ANOVA does not use a one-sided alternative")
            if self.allocation_ratio != 1:
                raise ValueError("The first ANOVA implementation requires balanced groups")
        if any(value <= 0 for value in self.sensitivity_effect_sizes):
            raise ValueError("Sensitivity effect sizes must be positive")
        if any(value <= 0 or value >= 1 for value in self.sensitivity_powers):
            raise ValueError("Sensitivity powers must be between zero and one")
        return self


class PowerScenario(BaseModel):
    effect_size: float
    target_power: float
    nominal_total_n: int = Field(ge=2)
    adjusted_total_n: int = Field(ge=2)
    nominal_per_group: list[int] = Field(min_length=1)
    adjusted_per_group: list[int] = Field(min_length=1)


class PowerAnalysis(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    source_plan_id: UUID
    source_plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    request: PowerAnalysisRequest
    primary_result: PowerScenario
    sensitivity_results: list[PowerScenario]
    method: str
    package_versions: dict[str, str]
    status: PreparationStatus = PreparationStatus.PENDING_REVIEW
    generation: GenerationMetadata
    reviewer_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def review(self, request: "PowerAnalysisReviewRequest") -> "PowerAnalysis":
        return self.model_copy(
            update={
                "status": request.status,
                "reviewer_note": request.note,
                "reviewed_at": utc_now(),
                "updated_at": utc_now(),
            }
        )

    def mark_stale(self) -> "PowerAnalysis":
        return self.model_copy(
            update={"status": PreparationStatus.STALE, "updated_at": utc_now()}
        )


class PowerAnalysisReviewRequest(BaseModel):
    status: PreparationStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_review(self) -> "PowerAnalysisReviewRequest":
        if self.status not in {
            PreparationStatus.APPROVED,
            PreparationStatus.NEEDS_REVISION,
        }:
            raise ValueError("Power review must approve or request revision")
        if self.status is PreparationStatus.NEEDS_REVISION and not self.note:
            raise ValueError("A revision request requires a note")
        return self


class DataType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    CATEGORY = "category"
    BOOLEAN = "boolean"
    DATETIME = "datetime"


class DataFieldRole(StrEnum):
    IDENTIFIER = "identifier"
    CONDITION = "condition"
    TRIAL = "trial"
    TIMESTAMP = "timestamp"
    INDEPENDENT = "independent"
    DEPENDENT = "dependent"
    CONTROL = "control"
    COVARIATE = "covariate"
    MANIPULATION_CHECK = "manipulation_check"


class DataField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(pattern=r"^[a-z][a-z0-9_]{1,63}$")
    label: str = Field(min_length=2, max_length=300)
    role: DataFieldRole
    data_type: DataType
    unit: str | None
    required: bool
    allowed_min: float | None
    allowed_max: float | None
    categories: list[str]
    missing_values: list[str]
    measurement_timing: str = Field(min_length=2, max_length=500)
    source: str = Field(min_length=2, max_length=1000)
    sensitive: bool
    validation_rules: list[str]

    @model_validator(mode="after")
    def validate_constraints(self) -> "DataField":
        if (
            self.allowed_min is not None
            and self.allowed_max is not None
            and self.allowed_min > self.allowed_max
        ):
            raise ValueError("allowed_min must not exceed allowed_max")
        if self.data_type is DataType.CATEGORY and not self.categories:
            raise ValueError("Category fields require allowed categories")
        return self


class DataContractContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row_grain: str = Field(min_length=3, max_length=1000)
    primary_key_fields: list[str] = Field(min_length=1)
    fields: list[DataField] = Field(min_length=5, max_length=100)
    collection_notes: list[str]

    @model_validator(mode="after")
    def validate_contract(self) -> "DataContractContent":
        keys = [field.key for field in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError("Data field keys must be unique")
        if not set(self.primary_key_fields).issubset(keys):
            raise ValueError("Primary key fields must exist in the data contract")
        return self


class DataContract(DataContractContent):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    source_plan_id: UUID
    source_plan_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: PreparationStatus = PreparationStatus.PENDING_REVIEW
    generation: GenerationMetadata
    reviewer_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def review(self, request: "DataContractReviewRequest") -> "DataContract":
        return DataContract(
            **request.content.model_dump(),
            id=self.id,
            project_id=self.project_id,
            source_plan_id=self.source_plan_id,
            source_plan_hash=self.source_plan_hash,
            status=request.status,
            generation=GenerationMetadata(
                generator="human",
                model=None,
                prompt_version="manual-data-contract-review",
            ),
            reviewer_note=request.note,
            reviewed_at=utc_now(),
            created_at=self.created_at,
            updated_at=utc_now(),
        )

    def mark_stale(self) -> "DataContract":
        return self.model_copy(
            update={"status": PreparationStatus.STALE, "updated_at": utc_now()}
        )


class DataContractReviewRequest(BaseModel):
    content: DataContractContent
    status: PreparationStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_review(self) -> "DataContractReviewRequest":
        if self.status not in {
            PreparationStatus.APPROVED,
            PreparationStatus.NEEDS_REVISION,
        }:
            raise ValueError("Data-contract review must approve or request revision")
        if self.status is PreparationStatus.NEEDS_REVISION and not self.note:
            raise ValueError("A revision request requires a note")
        return self


class StudyPreparation(BaseModel):
    project_id: UUID
    power_analysis: PowerAnalysis | None = None
    data_contract: DataContract | None = None
    updated_at: datetime = Field(default_factory=utc_now)

    def with_power_analysis(self, analysis: PowerAnalysis) -> "StudyPreparation":
        return self.model_copy(
            update={"power_analysis": analysis, "updated_at": utc_now()}
        )

    def with_data_contract(self, contract: DataContract) -> "StudyPreparation":
        return self.model_copy(
            update={"data_contract": contract, "updated_at": utc_now()}
        )


VARIABLE_ROLE_TO_DATA_ROLE = {
    VariableRole.INDEPENDENT: DataFieldRole.INDEPENDENT,
    VariableRole.DEPENDENT: DataFieldRole.DEPENDENT,
    VariableRole.CONTROL: DataFieldRole.CONTROL,
    VariableRole.COVARIATE: DataFieldRole.COVARIATE,
    VariableRole.MANIPULATION_CHECK: DataFieldRole.MANIPULATION_CHECK,
}
