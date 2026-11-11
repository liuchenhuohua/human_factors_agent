from typing import Protocol
from uuid import UUID

from app.domain.evidence import (
    EvidenceReview,
    LiteratureCandidate,
    SearchPlan,
    SearchPlanContent,
)
from app.domain.project import Project


class EvidencePlanningError(RuntimeError):
    pass


class LiteratureSearchError(RuntimeError):
    pass


class EvidencePlanner(Protocol):
    def plan(self, project: Project) -> SearchPlan: ...


class LiteratureSearch(Protocol):
    def search(self, plan: SearchPlanContent) -> list[LiteratureCandidate]: ...


class EvidenceStore(Protocol):
    def save(self, review: EvidenceReview) -> None: ...

    def get_by_project(self, project_id: UUID) -> EvidenceReview | None: ...
