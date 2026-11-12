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
            update={"evidence_items": updated_items, "updated_at": utc_now()}
        )
