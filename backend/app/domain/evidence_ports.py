from typing import Protocol
from uuid import UUID

from app.domain.evidence import (
    EvidenceDocument,
    EvidenceAppraisal,
    EvidenceItem,
    EvidenceReview,
    EvidenceSynthesis,
    LiteratureCandidate,
    ParsedDocument,
    SearchPlan,
    SearchPlanContent,
)
from app.domain.project import Project


class EvidencePlanningError(RuntimeError):
    pass


class LiteratureSearchError(RuntimeError):
    pass


class DocumentValidationError(ValueError):
    pass


class DocumentParsingError(RuntimeError):
    pass


class EvidenceExtractionError(RuntimeError):
    pass


class EvidenceAppraisalError(RuntimeError):
    pass


class EvidenceSynthesisError(RuntimeError):
    pass


class EvidencePlanner(Protocol):
    def plan(self, project: Project) -> SearchPlan: ...


class LiteratureSearch(Protocol):
    def search(self, plan: SearchPlanContent) -> list[LiteratureCandidate]: ...


class DocumentStorage(Protocol):
    def save(
        self,
        project_id: UUID,
        candidate_id: UUID,
        filename: str,
        content_type: str,
        content: bytes,
        page_count: int,
    ) -> EvidenceDocument: ...

    def read(self, storage_key: str) -> bytes: ...

    def delete(self, storage_key: str) -> None: ...


class PdfTextExtractor(Protocol):
    def parse(self, content: bytes) -> ParsedDocument: ...


class EvidenceExtractor(Protocol):
    def extract(
        self,
        candidate: LiteratureCandidate,
        document: EvidenceDocument,
        parsed: ParsedDocument,
    ) -> EvidenceItem: ...


class EvidenceAppraiser(Protocol):
    def appraise(
        self,
        project: Project,
        candidate: LiteratureCandidate,
        item: EvidenceItem,
    ) -> EvidenceAppraisal: ...


class EvidenceSynthesizer(Protocol):
    def synthesize(
        self,
        project: Project,
        review: EvidenceReview,
    ) -> EvidenceSynthesis: ...


class EvidenceStore(Protocol):
    def save(self, review: EvidenceReview) -> None: ...

    def get_by_project(self, project_id: UUID) -> EvidenceReview | None: ...
