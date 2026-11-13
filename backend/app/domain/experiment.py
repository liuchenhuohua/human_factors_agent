from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.project import GenerationMetadata, utc_now


class ExperimentStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    STALE = "stale"


class ExperimentDesignType(StrEnum):
    UNDECIDED = "undecided"
    WITHIN_SUBJECTS = "within_subjects"
    BETWEEN_SUBJECTS = "between_subjects"
    MIXED = "mixed"
    QUASI_EXPERIMENTAL = "quasi_experimental"


class HypothesisDirection(StrEnum):
    NON_DIRECTIONAL = "non_directional"
    INCREASE = "increase"
    DECREASE = "decrease"


class VariableRole(StrEnum):
    INDEPENDENT = "independent"
    DEPENDENT = "dependent"
    CONTROL = "control"
    COVARIATE = "covariate"
    MANIPULATION_CHECK = "manipulation_check"


class ExperimentHypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=5, max_length=2000)
    null_hypothesis: str = Field(min_length=5, max_length=2000)
    direction: HypothesisDirection
    primary_outcome: str = Field(min_length=2, max_length=500)
    evidence_item_ids: list[UUID] = Field(min_length=1)


class ExperimentalCondition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=3, max_length=1500)


class VariableSpecification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=300)
    role: VariableRole
    operational_definition: str = Field(min_length=3, max_length=2000)
    measurement_method: str = Field(min_length=2, max_length=1000)
    measurement_timing: str = Field(min_length=2, max_length=500)
    evidence_item_ids: list[UUID] = Field(min_length=1)


class ParticipantPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_population: str = Field(min_length=2, max_length=1000)
    inclusion_criteria: list[str] = Field(min_length=1, max_length=20)
    exclusion_criteria: list[str] = Field(min_length=1, max_length=20)
    recruitment_strategy: str = Field(min_length=3, max_length=1500)
    sampling_method: str = Field(min_length=3, max_length=500)


class SampleSizePlanning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    planned_primary_test: str = Field(min_length=3, max_length=500)
    effect_size_metric: str | None = Field(min_length=1)
    expected_effect_size: float | None = Field(gt=0)
    effect_size_basis: str = Field(min_length=3, max_length=1500)
    alpha: float | None = Field(gt=0, lt=1)
    target_power: float | None = Field(gt=0, lt=1)
    attrition_allowance: float | None = Field(ge=0, lt=1)
    calculation_note: str = Field(min_length=3, max_length=1500)


class ProcedureStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int = Field(ge=1)
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=3, max_length=2000)
    duration_minutes: int | None = Field(ge=1)
    data_collected: list[str]


class StatisticalAnalysisPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_index: int = Field(ge=1)
    method: str = Field(min_length=3, max_length=1000)
    outcome: str = Field(min_length=2, max_length=500)
    predictors: list[str] = Field(min_length=1)
    assumptions_to_check: list[str]
    missing_data_strategy: str = Field(min_length=3, max_length=1000)
    multiplicity_strategy: str = Field(min_length=3, max_length=1000)


class EvidenceGroundedDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(min_length=3, max_length=2000)
    rationale: str = Field(min_length=3, max_length=2000)
    evidence_item_ids: list[UUID] = Field(min_length=1)


class ExperimentPlanContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=300)
    objective: str = Field(min_length=10, max_length=3000)
    design_type: ExperimentDesignType
    hypotheses: list[ExperimentHypothesis] = Field(min_length=1, max_length=12)
    conditions: list[ExperimentalCondition] = Field(min_length=2, max_length=12)
    variables: list[VariableSpecification] = Field(min_length=2, max_length=40)
    participant_plan: ParticipantPlan
    sample_size_planning: SampleSizePlanning
    randomization_plan: str = Field(min_length=3, max_length=2000)
    counterbalancing_plan: str = Field(min_length=3, max_length=2000)
    procedure: list[ProcedureStep] = Field(min_length=1, max_length=30)
    analysis_plan: list[StatisticalAnalysisPlan] = Field(min_length=1, max_length=12)
    ethics_and_safety: list[str] = Field(min_length=1, max_length=20)
    assumptions: list[str] = Field(min_length=1, max_length=20)
    uncertainties: list[str] = Field(min_length=1, max_length=20)
    evidence_grounded_decisions: list[EvidenceGroundedDecision] = Field(
        min_length=1,
        max_length=30,
    )

    @model_validator(mode="after")
    def validate_plan_structure(self) -> "ExperimentPlanContent":
        roles = {variable.role for variable in self.variables}
        if VariableRole.INDEPENDENT not in roles:
            raise ValueError("Experiment plan requires an independent variable")
        if VariableRole.DEPENDENT not in roles:
            raise ValueError("Experiment plan requires a dependent variable")
        if any(
            analysis.hypothesis_index > len(self.hypotheses)
            for analysis in self.analysis_plan
        ):
            raise ValueError("Analysis plan references a missing hypothesis")
        orders = [step.order for step in self.procedure]
        if len(orders) != len(set(orders)):
            raise ValueError("Procedure step orders must be unique")
        return self


class ExperimentPlan(ExperimentPlanContent):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    source_synthesis_id: UUID
    source_synthesis_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: ExperimentStatus = ExperimentStatus.PENDING_REVIEW
    generation: GenerationMetadata
    reviewer_note: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def review(self, request: "ExperimentPlanReviewRequest") -> "ExperimentPlan":
        return ExperimentPlan(
            **request.content.model_dump(),
            id=self.id,
            project_id=self.project_id,
            source_synthesis_id=self.source_synthesis_id,
            source_synthesis_hash=self.source_synthesis_hash,
            status=request.status,
            generation=GenerationMetadata(
                generator="human",
                model=None,
                prompt_version="manual-experiment-review",
            ),
            reviewer_note=request.note,
            reviewed_at=utc_now(),
            created_at=self.created_at,
            updated_at=utc_now(),
        )

    def mark_stale(self) -> "ExperimentPlan":
        if self.status is ExperimentStatus.STALE:
            return self
        return self.model_copy(
            update={"status": ExperimentStatus.STALE, "updated_at": utc_now()}
        )


class ExperimentPlanReviewRequest(BaseModel):
    content: ExperimentPlanContent
    status: ExperimentStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_review(self) -> "ExperimentPlanReviewRequest":
        if self.status not in {
            ExperimentStatus.APPROVED,
            ExperimentStatus.NEEDS_REVISION,
        }:
            raise ValueError("Experiment review must approve or request revision")
        if self.status is ExperimentStatus.NEEDS_REVISION and not self.note:
            raise ValueError("A revision request requires a note")
        return self
