from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.project import GenerationMetadata, utc_now


class EvidenceStage(StrEnum):
    SEARCH_PLAN_REVIEW = "search_plan_review"
    SCREENING = "screening"


class SearchPlanContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=1000)
    keywords: list[str] = Field(min_length=3, max_length=20)
    inclusion_criteria: list[str] = Field(min_length=1, max_length=12)
    exclusion_criteria: list[str] = Field(min_length=1, max_length=12)
    from_year: int | None = Field(ge=1900, le=2100)
    until_year: int | None = Field(ge=1900, le=2100)
    max_results: int = Field(ge=5, le=50)

    @model_validator(mode="after")
    def validate_year_range(self) -> "SearchPlanContent":
        if self.from_year and self.until_year and self.from_year > self.until_year:
            raise ValueError("from_year must not be later than until_year")
        return self


class SearchPlan(SearchPlanContent):
    generation: GenerationMetadata


class ScreeningStatus(StrEnum):
    UNSCREENED = "unscreened"
    INCLUDED = "included"
    EXCLUDED = "excluded"


class LiteratureCandidate(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    source: str
    source_id: str
    doi: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    publication_year: int | None = None
    venue: str | None = None
    url: str
    work_type: str | None = None
    screening_status: ScreeningStatus = ScreeningStatus.UNSCREENED
    screening_reason: str | None = None
    retrieved_at: datetime = Field(default_factory=utc_now)


class EvidenceDocument(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    candidate_id: UUID
    filename: str
    content_type: str = "application/pdf"
    byte_size: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    storage_key: str
    page_count: int = Field(ge=1)
    uploaded_at: datetime = Field(default_factory=utc_now)


class ParsedPage(BaseModel):
    page_number: int = Field(ge=1)
    text: str


class ParsedDocument(BaseModel):
    pages: list[ParsedPage] = Field(min_length=1)

    @property
    def text_length(self) -> int:
        return sum(len(page.text) for page in self.pages)


class SourceExcerpt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    text: str = Field(min_length=1, max_length=2000)
    relevance: str = Field(min_length=1, max_length=500)


class EvidenceItemContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_questions: list[str]
    study_design: str | None
    participants: str | None
    sample_size: int | None = Field(ge=1)
    task_context: str | None
    independent_variables: list[str]
    dependent_variables: list[str]
    control_variables: list[str]
    measures: list[str]
    statistical_methods: list[str]
    key_findings: list[str]
    effect_sizes: list[str]
    limitations: list[str]
    source_excerpts: list[SourceExcerpt] = Field(min_length=1, max_length=20)


class EvidenceItemStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"


class EvidenceItem(EvidenceItemContent):
    id: UUID = Field(default_factory=uuid4)
    candidate_id: UUID
    document_id: UUID
    status: EvidenceItemStatus = EvidenceItemStatus.PENDING_REVIEW
    generation: GenerationMetadata
    reviewer_note: str | None = None
    reviewed_at: datetime | None = None


class EvidenceItemReviewRequest(BaseModel):
    content: EvidenceItemContent
    status: EvidenceItemStatus
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("note")
    @classmethod
    def strip_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def validate_review(self) -> "EvidenceItemReviewRequest":
        if self.status is EvidenceItemStatus.PENDING_REVIEW:
            raise ValueError("A review must approve the item or request revision")
        if self.status is EvidenceItemStatus.NEEDS_REVISION and not self.note:
            raise ValueError("A revision request requires a note")
        return self


class AppraisalConcern(StrEnum):
    LOW = "low"
    SOME_CONCERNS = "some_concerns"
    HIGH = "high"
    UNCLEAR = "unclear"


class AppraisalConfidence(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    UNCLEAR = "unclear"


class AppraisalJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concern: AppraisalConcern
    rationale: str = Field(min_length=3, max_length=1500)


class EvidenceAppraisalContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    design_appropriateness: AppraisalJudgment
    sample_adequacy: AppraisalJudgment
    measurement_validity: AppraisalJudgment
    analysis_adequacy: AppraisalJudgment
    bias_risk: AppraisalJudgment
    directness: AppraisalJudgment
    overall_confidence: AppraisalConfidence
    strengths: list[str] = Field(max_length=12)
    concerns: list[str] = Field(max_length=12)


class ReviewStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"


class EvidenceAppraisal(EvidenceAppraisalContent):
    id: UUID = Field(default_factory=uuid4)
    evidence_item_id: UUID
    status: ReviewStatus = ReviewStatus.PENDING_REVIEW
    generation: GenerationMetadata
    reviewer_note: str | None = None
    reviewed_at: datetime | None = None


class EvidenceAppraisalReviewRequest(BaseModel):
    content: EvidenceAppraisalContent
    status: ReviewStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_review(self) -> "EvidenceAppraisalReviewRequest":
        if self.status is ReviewStatus.PENDING_REVIEW:
            raise ValueError("An appraisal review must approve or request revision")
        if self.status is ReviewStatus.NEEDS_REVISION and not self.note:
            raise ValueError("A revision request requires a note")
        return self


class EvidenceMatrixRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_item_id: UUID
    candidate_id: UUID
    citation: str
    population_and_context: str
    design_and_sample: str
    exposures_or_interventions: list[str]
    outcomes_and_measures: list[str]
    findings_and_effects: list[str]
    limitations: list[str]
    appraisal_confidence: AppraisalConfidence


class SynthesisClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=3, max_length=3000)
    evidence_item_ids: list[UUID] = Field(min_length=1)
    confidence: AppraisalConfidence
    rationale: str = Field(min_length=3, max_length=2000)


class EvidenceSynthesisContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    matrix: list[EvidenceMatrixRow] = Field(min_length=1)
    consistent_findings: list[SynthesisClaim]
    conflicting_findings: list[SynthesisClaim]
    evidence_gaps: list[str]
    transferability_notes: list[str]
    cautions: list[str]


class EvidenceSynthesis(EvidenceSynthesisContent):
    id: UUID = Field(default_factory=uuid4)
    status: ReviewStatus = ReviewStatus.PENDING_REVIEW
    generation: GenerationMetadata
    reviewer_note: str | None = None
    reviewed_at: datetime | None = None


class EvidenceSynthesisReviewRequest(BaseModel):
    content: EvidenceSynthesisContent
    status: ReviewStatus
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_review(self) -> "EvidenceSynthesisReviewRequest":
        if self.status is ReviewStatus.PENDING_REVIEW:
            raise ValueError("A synthesis review must approve or request revision")
        if self.status is ReviewStatus.NEEDS_REVISION and not self.note:
            raise ValueError("A revision request requires a note")
        return self


class ScreeningRequest(BaseModel):
    status: ScreeningStatus
    reason: str = Field(min_length=3, max_length=1000)

    @field_validator("status")
    @classmethod
    def disallow_unscreened(cls, value: ScreeningStatus) -> ScreeningStatus:
        if value is ScreeningStatus.UNSCREENED:
            raise ValueError("Screening decision must include or exclude the candidate")
        return value

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        return value.strip()


class EvidenceReview(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    stage: EvidenceStage = EvidenceStage.SEARCH_PLAN_REVIEW
    search_plan: SearchPlan
    candidates: list[LiteratureCandidate] = Field(default_factory=list)
    documents: list[EvidenceDocument] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    appraisals: list[EvidenceAppraisal] = Field(default_factory=list)
    synthesis: EvidenceSynthesis | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def with_search_plan(self, content: SearchPlanContent) -> "EvidenceReview":
        plan = SearchPlan(
            **content.model_dump(),
            generation=GenerationMetadata(
                generator="human",
                model=None,
                prompt_version="manual-edit",
            ),
        )
        return self.model_copy(update={"search_plan": plan, "updated_at": utc_now()})

    def with_candidates(
        self, candidates: list[LiteratureCandidate]
    ) -> "EvidenceReview":
        return self.model_copy(
            update={
                "candidates": candidates,
                "stage": EvidenceStage.SCREENING,
                "updated_at": utc_now(),
            }
        )

    def screen_candidate(
        self, candidate_id: UUID, request: ScreeningRequest
    ) -> "EvidenceReview":
        if request.status is ScreeningStatus.EXCLUDED and any(
            document.candidate_id == candidate_id for document in self.documents
        ):
            raise ValueError(
                "A candidate with extracted evidence cannot be excluded in this version"
            )
        found = False
        updated_candidates: list[LiteratureCandidate] = []
        for candidate in self.candidates:
            if candidate.id == candidate_id:
                found = True
                candidate = candidate.model_copy(
                    update={
                        "screening_status": request.status,
                        "screening_reason": request.reason,
                    }
                )
            updated_candidates.append(candidate)
        if not found:
            raise KeyError(f"Candidate {candidate_id} not found")
        return self.model_copy(
            update={"candidates": updated_candidates, "updated_at": utc_now()}
        )

    def require_included_candidate(self, candidate_id: UUID) -> LiteratureCandidate:
        candidate = next(
            (item for item in self.candidates if item.id == candidate_id),
            None,
        )
        if candidate is None:
            raise KeyError(f"Candidate {candidate_id} not found")
        if candidate.screening_status is not ScreeningStatus.INCLUDED:
            raise ValueError("Only included literature can receive a PDF")
        return candidate

    def with_extraction(
        self,
        document: EvidenceDocument,
        item: EvidenceItem,
    ) -> "EvidenceReview":
        if any(existing.candidate_id == document.candidate_id for existing in self.documents):
            raise ValueError("This literature candidate already has an uploaded PDF")
        if item.candidate_id != document.candidate_id or item.document_id != document.id:
            raise ValueError("Evidence item does not match its source document")
        return self.model_copy(
            update={
                "documents": [*self.documents, document],
                "evidence_items": [*self.evidence_items, item],
                "updated_at": utc_now(),
            }
        )

    def review_evidence_item(
        self,
        item_id: UUID,
        request: EvidenceItemReviewRequest,
    ) -> "EvidenceReview":
        found = False
        updated_items: list[EvidenceItem] = []
        for item in self.evidence_items:
            if item.id == item_id:
                found = True
                item = EvidenceItem(
                    **request.content.model_dump(),
                    id=item.id,
                    candidate_id=item.candidate_id,
                    document_id=item.document_id,
                    status=request.status,
                    generation=GenerationMetadata(
                        generator="human",
                        model=None,
                        prompt_version="manual-evidence-review",
                    ),
                    reviewer_note=request.note,
                    reviewed_at=utc_now(),
                )
            updated_items.append(item)
        if not found:
            raise KeyError(f"Evidence item {item_id} not found")
        return self.model_copy(
            update={
                "evidence_items": updated_items,
                "appraisals": [
                    appraisal
                    for appraisal in self.appraisals
                    if appraisal.evidence_item_id != item_id
                ],
                "synthesis": None,
                "updated_at": utc_now(),
            }
        )

    def with_appraisal(self, appraisal: EvidenceAppraisal) -> "EvidenceReview":
        item = next(
            (item for item in self.evidence_items if item.id == appraisal.evidence_item_id),
            None,
        )
        if item is None:
            raise KeyError(f"Evidence item {appraisal.evidence_item_id} not found")
        if item.status is not EvidenceItemStatus.APPROVED:
            raise ValueError("Only approved evidence items can be appraised")
        if any(
            existing.evidence_item_id == appraisal.evidence_item_id
            for existing in self.appraisals
        ):
            raise ValueError("This evidence item already has an appraisal")
        return self.model_copy(
            update={
                "appraisals": [*self.appraisals, appraisal],
                "synthesis": None,
                "updated_at": utc_now(),
            }
        )

    def review_appraisal(
        self,
        appraisal_id: UUID,
        request: EvidenceAppraisalReviewRequest,
    ) -> "EvidenceReview":
        found = False
        updated: list[EvidenceAppraisal] = []
        for appraisal in self.appraisals:
            if appraisal.id == appraisal_id:
                found = True
                appraisal = EvidenceAppraisal(
                    **request.content.model_dump(),
                    id=appraisal.id,
                    evidence_item_id=appraisal.evidence_item_id,
                    status=request.status,
                    generation=GenerationMetadata(
                        generator="human",
                        model=None,
                        prompt_version="manual-appraisal-review",
                    ),
                    reviewer_note=request.note,
                    reviewed_at=utc_now(),
                )
            updated.append(appraisal)
        if not found:
            raise KeyError(f"Evidence appraisal {appraisal_id} not found")
        return self.model_copy(
            update={"appraisals": updated, "synthesis": None, "updated_at": utc_now()}
        )

    def approved_evidence_with_appraisals(
        self,
    ) -> list[tuple[EvidenceItem, EvidenceAppraisal]]:
        approved_items = [
            item for item in self.evidence_items if item.status is EvidenceItemStatus.APPROVED
        ]
        if not approved_items:
            raise ValueError("At least one approved evidence item is required")
        appraisal_by_item = {
            appraisal.evidence_item_id: appraisal
            for appraisal in self.appraisals
            if appraisal.status is ReviewStatus.APPROVED
        }
        missing = [item.id for item in approved_items if item.id not in appraisal_by_item]
        if missing:
            raise ValueError("Every approved evidence item needs an approved appraisal")
        return [(item, appraisal_by_item[item.id]) for item in approved_items]

    def with_synthesis(self, synthesis: EvidenceSynthesis) -> "EvidenceReview":
        self._validate_synthesis_content(synthesis)
        return self.model_copy(
            update={"synthesis": synthesis, "updated_at": utc_now()}
        )

    def review_synthesis(
        self,
        request: EvidenceSynthesisReviewRequest,
    ) -> "EvidenceReview":
        if self.synthesis is None:
            raise KeyError("Evidence synthesis not found")
        self._validate_synthesis_content(request.content)
        synthesis = EvidenceSynthesis(
            **request.content.model_dump(),
            id=self.synthesis.id,
            status=request.status,
            generation=GenerationMetadata(
                generator="human",
                model=None,
                prompt_version="manual-synthesis-review",
            ),
            reviewer_note=request.note,
            reviewed_at=utc_now(),
        )
        return self.model_copy(update={"synthesis": synthesis, "updated_at": utc_now()})

    def _validate_synthesis_content(
        self,
        content: EvidenceSynthesisContent,
    ) -> None:
        pairs = self.approved_evidence_with_appraisals()
        items = {item.id: item for item, _ in pairs}
        matrix_ids = [row.evidence_item_id for row in content.matrix]
        if len(matrix_ids) != len(set(matrix_ids)) or set(matrix_ids) != set(items):
            raise ValueError(
                "The evidence matrix must contain each approved evidence item exactly once"
            )
        for row in content.matrix:
            if row.candidate_id != items[row.evidence_item_id].candidate_id:
                raise ValueError("A matrix row does not match its evidence item")
        for claim in [
            *content.consistent_findings,
            *content.conflicting_findings,
        ]:
            referenced = set(claim.evidence_item_ids)
            if not referenced.issubset(items):
                raise ValueError("A synthesis claim references unapproved evidence")
            if len(referenced) < 2:
                raise ValueError(
                    "A cross-study synthesis claim requires at least two evidence items"
                )
