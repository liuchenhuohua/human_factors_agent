from typing import Any, TypedDict
from uuid import UUID

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.domain.ports import ProblemFramer, ProjectStore
from app.domain.project import ProblemFrame, Project, ProjectIntake


class ProjectGraphState(TypedDict, total=False):
    project_id: str
    intake: dict[str, Any]
    problem_frame: dict[str, Any]
    approval: dict[str, Any]
    stage: str


class ProjectWorkflow:
    """Small interface around framing, approval interruption and persistence."""

    def __init__(self, framer: ProblemFramer, store: ProjectStore) -> None:
        self._framer = framer
        self._store = store
        self._graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(ProjectGraphState)
        graph.add_node("frame_problem", self._frame_problem)
        graph.add_node("review_problem_frame", self._review_problem_frame)
        graph.add_edge(START, "frame_problem")
        graph.add_edge("frame_problem", "review_problem_frame")
        graph.add_edge("review_problem_frame", END)
        return graph.compile(checkpointer=InMemorySaver())

    def start(self, intake: ProjectIntake) -> Project:
        project = Project(intake=intake)
        self._store.save(project)
        config = self._config(project.id)
        self._graph.invoke(
            {"project_id": str(project.id), "intake": intake.model_dump(mode="json")},
            config=config,
        )
        stored = self._store.get(project.id)
        if stored is None:
            raise RuntimeError("Project disappeared after workflow start")
        return stored

    def approve_problem_frame(self, project_id: UUID) -> Project:
        project = self._require_project(project_id)
        self._graph.invoke(
            Command(resume={"approved": True}),
            config=self._config(project_id),
        )
        stored = self._store.get(project_id)
        if stored is None:
            raise RuntimeError("Project disappeared after approval")
        return stored

    def get(self, project_id: UUID) -> Project | None:
        return self._store.get(project_id)

    def list(self) -> list[Project]:
        return self._store.list()

    def _frame_problem(self, state: ProjectGraphState) -> ProjectGraphState:
        project_id = UUID(state["project_id"])
        intake = ProjectIntake.model_validate(state["intake"])
        problem_frame = self._framer.frame(intake)
        project = self._require_project(project_id).with_problem_frame(problem_frame)
        self._store.save(project)
        return {
            "problem_frame": problem_frame.model_dump(mode="json"),
            "stage": project.stage.value,
        }

    def _review_problem_frame(self, state: ProjectGraphState) -> ProjectGraphState:
        decision = interrupt(
            {
                "kind": "problem_frame_review",
                "project_id": state["project_id"],
                "problem_frame": state["problem_frame"],
            }
        )
        if not decision.get("approved"):
            return {"approval": decision, "stage": "problem_frame_review"}

        project_id = UUID(state["project_id"])
        project = self._require_project(project_id).approve_problem_frame()
        self._store.save(project)
        return {"approval": decision, "stage": project.stage.value}

    def _require_project(self, project_id: UUID) -> Project:
        project = self._store.get(project_id)
        if project is None:
            raise KeyError(f"Project {project_id} not found")
        return project

    @staticmethod
    def _config(project_id: UUID) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": str(project_id)}}

