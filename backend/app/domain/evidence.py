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
