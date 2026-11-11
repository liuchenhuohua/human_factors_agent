from typing import Any, TypedDict
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.domain.evidence import (
    EvidenceReview,
    LiteratureCandidate,
    ScreeningRequest,
    SearchPlan,
    SearchPlanContent,
)
from app.domain.evidence_ports import (
    EvidencePlanner,
    EvidenceStore,
    LiteratureSearch,
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
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._planner = planner
        self._search = search
        self._project_store = project_store
        self._evidence_store = evidence_store
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

    @staticmethod
    def _config(project_id: UUID) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": f"evidence:{project_id}"}}
