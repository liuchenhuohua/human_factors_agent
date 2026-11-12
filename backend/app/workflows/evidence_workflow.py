from typing import Any, TypedDict
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.domain.evidence import (
    EvidenceAppraisalReviewRequest,
    EvidenceItemContent,
    EvidenceItemReviewRequest,
    EvidenceReview,
    EvidenceSynthesisReviewRequest,
    LiteratureCandidate,
    ParsedDocument,
    ScreeningRequest,
    SearchPlan,
    SearchPlanContent,
)
from app.domain.evidence_ports import (
    DocumentStorage,
    DocumentValidationError,
    EvidenceAppraiser,
    EvidenceExtractor,
    EvidencePlanner,
    EvidenceStore,
    EvidenceSynthesizer,
    LiteratureSearch,
    PdfTextExtractor,
)
from app.domain.ports import ProjectStore
from app.domain.project import Project, ProjectStage


class EvidenceGraphState(TypedDict, total=False):
    project_id: str
    search_plan: dict[str, Any]
    candidate_count: int


class EvidenceWorkflow:
    """Own search-plan approval, literature retrieval and screening state."""

    def __init__(
        self,
        planner: EvidencePlanner,
        search: LiteratureSearch,
        project_store: ProjectStore,
        evidence_store: EvidenceStore,
        document_storage: DocumentStorage,
        pdf_extractor: PdfTextExtractor,
        evidence_extractor: EvidenceExtractor,
        evidence_appraiser: EvidenceAppraiser,
        evidence_synthesizer: EvidenceSynthesizer,
        checkpointer: BaseCheckpointSaver | None = None,
        max_upload_bytes: int = 25 * 1024 * 1024,
    ) -> None:
        self._planner = planner
        self._search = search
        self._project_store = project_store
        self._evidence_store = evidence_store
        self._document_storage = document_storage
        self._pdf_extractor = pdf_extractor
        self._evidence_extractor = evidence_extractor
        self._evidence_appraiser = evidence_appraiser
        self._evidence_synthesizer = evidence_synthesizer
        self.max_upload_bytes = max_upload_bytes
        self._graph = self._build_graph(checkpointer or InMemorySaver())

    def _build_graph(self, checkpointer: BaseCheckpointSaver):
        graph = StateGraph(EvidenceGraphState)
        graph.add_node("review_search_plan", self._review_search_plan)
        graph.add_node("search_literature", self._search_literature)
        graph.add_node("await_screening", self._await_screening)
        graph.add_edge(START, "review_search_plan")
        graph.add_edge("review_search_plan", "search_literature")
        graph.add_edge("search_literature", "await_screening")
        graph.add_edge("await_screening", END)
        return graph.compile(checkpointer=checkpointer)

    def start(self, project_id: UUID) -> EvidenceReview:
        existing = self._evidence_store.get_by_project(project_id)
        if existing is not None:
            return existing
        project = self._require_approved_project(project_id)
        search_plan = self._planner.plan(project)
        review = EvidenceReview(project_id=project_id, search_plan=search_plan)
        self._evidence_store.save(review)
        self._graph.invoke(
            {
                "project_id": str(project_id),
                "search_plan": search_plan.model_dump(mode="json"),
            },
            config=self._config(project_id),
        )
        return self._require_review(project_id)

    def approve_search_plan(
        self, project_id: UUID, content: SearchPlanContent
    ) -> EvidenceReview:
        self._require_review(project_id)
        normalized = SearchPlanContent.model_validate(
            content.model_dump(include=set(SearchPlanContent.model_fields))
        )
        self._graph.invoke(
            Command(resume={"search_plan": normalized.model_dump(mode="json")}),
            config=self._config(project_id),
        )
        return self._require_review(project_id)

    def screen_candidate(
        self,
        project_id: UUID,
        candidate_id: UUID,
        request: ScreeningRequest,
    ) -> EvidenceReview:
        review = self._require_review(project_id).screen_candidate(candidate_id, request)
        self._evidence_store.save(review)
        return review

    def upload_pdf(
        self,
        project_id: UUID,
        candidate_id: UUID,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> EvidenceReview:
        review = self._require_review(project_id)
        candidate = review.require_included_candidate(candidate_id)
        self._validate_pdf(filename, content_type, content)
        if any(document.candidate_id == candidate_id for document in review.documents):
            raise ValueError("This literature candidate already has an uploaded PDF")
        parsed = self._pdf_extractor.parse(content)
        document = self._document_storage.save(
            project_id=project_id,
            candidate_id=candidate_id,
            filename=filename,
            content_type="application/pdf",
            content=content,
            page_count=len(parsed.pages),
        )
        try:
            item = self._evidence_extractor.extract(candidate, document, parsed)
            review = review.with_extraction(document, item)
            self._evidence_store.save(review)
        except Exception:
            self._document_storage.delete(document.storage_key)
            raise
        return review

    def review_evidence_item(
        self,
        project_id: UUID,
        item_id: UUID,
        request: EvidenceItemReviewRequest,
    ) -> EvidenceReview:
        review = self._require_review(project_id)
        item = next(
            (candidate for candidate in review.evidence_items if candidate.id == item_id),
            None,
        )
        if item is None:
            raise KeyError(f"Evidence item {item_id} not found")
        document = next(
            (candidate for candidate in review.documents if candidate.id == item.document_id),
            None,
        )
        if document is None:
            raise KeyError(f"Document {item.document_id} not found")
        try:
            parsed = self._pdf_extractor.parse(
                self._document_storage.read(document.storage_key)
            )
        except FileNotFoundError as error:
            raise DocumentValidationError("The source PDF is missing from storage") from error
        self._validate_source_excerpts(request.content, parsed)
        review = review.review_evidence_item(item_id, request)
        self._evidence_store.save(review)
        return review

    def appraise_evidence_item(
        self,
        project_id: UUID,
        item_id: UUID,
    ) -> EvidenceReview:
        project = self._require_approved_project(project_id)
        review = self._require_review(project_id)
        item = next(
            (item for item in review.evidence_items if item.id == item_id),
            None,
        )
        if item is None:
            raise KeyError(f"Evidence item {item_id} not found")
        candidate = next(
            (candidate for candidate in review.candidates if candidate.id == item.candidate_id),
            None,
        )
        if candidate is None:
            raise KeyError(f"Candidate {item.candidate_id} not found")
        appraisal = self._evidence_appraiser.appraise(project, candidate, item)
        review = review.with_appraisal(appraisal)
        self._evidence_store.save(review)
        return review

    def review_appraisal(
        self,
        project_id: UUID,
        appraisal_id: UUID,
        request: EvidenceAppraisalReviewRequest,
    ) -> EvidenceReview:
        review = self._require_review(project_id).review_appraisal(
            appraisal_id,
            request,
        )
        self._evidence_store.save(review)
        return review

    def generate_synthesis(self, project_id: UUID) -> EvidenceReview:
        project = self._require_approved_project(project_id)
        review = self._require_review(project_id)
        if review.synthesis is not None:
            return review
        synthesis = self._evidence_synthesizer.synthesize(project, review)
        review = review.with_synthesis(synthesis)
        self._evidence_store.save(review)
        return review

    def review_synthesis(
        self,
        project_id: UUID,
        request: EvidenceSynthesisReviewRequest,
    ) -> EvidenceReview:
        review = self._require_review(project_id).review_synthesis(request)
        self._evidence_store.save(review)
        return review

    def get(self, project_id: UUID) -> EvidenceReview | None:
        return self._evidence_store.get_by_project(project_id)

    def _review_search_plan(self, state: EvidenceGraphState) -> EvidenceGraphState:
        submission = interrupt(
            {
                "kind": "search_plan_review",
                "project_id": state["project_id"],
                "search_plan": state["search_plan"],
            }
        )
        submitted_plan = dict(submission["search_plan"])
        submitted_plan.pop("generation", None)
        content = SearchPlanContent.model_validate(submitted_plan)
        project_id = UUID(state["project_id"])
        review = self._require_review(project_id).with_search_plan(content)
        self._evidence_store.save(review)
        return {"search_plan": review.search_plan.model_dump(mode="json")}

    def _search_literature(self, state: EvidenceGraphState) -> EvidenceGraphState:
        project_id = UUID(state["project_id"])
        review = self._require_review(project_id)
        candidates = self._search.search(review.search_plan)
        review = review.with_candidates(candidates)
        self._evidence_store.save(review)
        return {"candidate_count": len(candidates)}

    def _await_screening(self, state: EvidenceGraphState) -> EvidenceGraphState:
        interrupt(
            {
                "kind": "literature_screening",
                "project_id": state["project_id"],
                "candidate_count": state["candidate_count"],
            }
        )
        return state

    def _require_approved_project(self, project_id: UUID) -> Project:
        project = self._project_store.get(project_id)
        if project is None:
            raise KeyError(f"Project {project_id} not found")
        if project.stage is not ProjectStage.PROBLEM_FRAME_APPROVED:
            raise ValueError("Problem frame must be approved before evidence search")
        return project

    def _require_review(self, project_id: UUID) -> EvidenceReview:
        review = self._evidence_store.get_by_project(project_id)
        if review is None:
            raise KeyError(f"Evidence review for project {project_id} not found")
        return review

    def _validate_pdf(
        self,
        filename: str,
        content_type: str | None,
        content: bytes,
    ) -> None:
        if not filename or not filename.lower().endswith(".pdf"):
            raise DocumentValidationError("Only .pdf files are accepted")
        if content_type not in {None, "", "application/pdf", "application/octet-stream"}:
            raise DocumentValidationError("Uploaded document must use a PDF content type")
        if not content:
            raise DocumentValidationError("Uploaded PDF is empty")
        if len(content) > self.max_upload_bytes:
            limit_mb = self.max_upload_bytes // (1024 * 1024)
            raise DocumentValidationError(f"Uploaded PDF exceeds the {limit_mb} MB limit")
        if b"%PDF-" not in content[:1024]:
            raise DocumentValidationError("Uploaded file does not have a valid PDF header")

    @staticmethod
    def _validate_source_excerpts(
        content: EvidenceItemContent,
        parsed: ParsedDocument,
    ) -> None:
        pages = {page.page_number: page.text for page in parsed.pages}
        for excerpt in content.source_excerpts:
            page_text = pages.get(excerpt.page_number)
            normalized_page = " ".join(page_text.split()) if page_text else ""
            normalized_excerpt = " ".join(excerpt.text.split())
            if not normalized_page or normalized_excerpt not in normalized_page:
                raise DocumentValidationError(
                    f"Source excerpt could not be verified on page {excerpt.page_number}"
                )

    @staticmethod
    def _config(project_id: UUID) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": f"evidence:{project_id}"}}
