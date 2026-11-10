from typing import Any, Literal, TypedDict
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from app.domain.ports import ProblemFramer, ProjectStore
from app.domain.project import ProblemFrameContent, Project, ProjectIntake


class ProjectGraphState(TypedDict, total=False):
    project_id: str
    intake: dict[str, Any]
    clarification_questions: list[dict[str, Any]]
    clarification_answers: dict[str, str]
    problem_frame: dict[str, Any]
    approval: dict[str, Any]
    stage: str


class ProjectWorkflow:
    """Own the framing workflow, human interruptions and project persistence."""

    def __init__(
        self,
        framer: ProblemFramer,
        store: ProjectStore,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._framer = framer
        self._store = store
        self._graph = self._build_graph(checkpointer or InMemorySaver())

    def _build_graph(self, checkpointer: BaseCheckpointSaver):
        graph = StateGraph(ProjectGraphState)
        graph.add_node("identify_gaps", self._identify_gaps)
        graph.add_node("collect_clarifications", self._collect_clarifications)
        graph.add_node("frame_problem", self._frame_problem)
        graph.add_node("review_problem_frame", self._review_problem_frame)
        graph.add_node("revise_problem_frame", self._revise_problem_frame)
        graph.add_node("approve_problem_frame", self._approve_problem_frame)

        graph.add_edge(START, "identify_gaps")
        graph.add_edge("identify_gaps", "collect_clarifications")
        graph.add_edge("collect_clarifications", "frame_problem")
        graph.add_edge("frame_problem", "review_problem_frame")
        graph.add_conditional_edges(
            "review_problem_frame",
            self._route_review,
            {
                "approve": "approve_problem_frame",
                "revise": "revise_problem_frame",
            },
        )
        graph.add_edge("revise_problem_frame", "review_problem_frame")
        graph.add_edge("approve_problem_frame", END)
        return graph.compile(checkpointer=checkpointer)

    def start(self, intake: ProjectIntake) -> Project:
        project = Project(intake=intake)
        self._store.save(project)
        self._graph.invoke(
            {"project_id": str(project.id), "intake": intake.model_dump(mode="json")},
            config=self._config(project.id),
        )
        return self._require_project(project.id)

    def submit_clarifications(
        self, project_id: UUID, answers: dict[str, str]
    ) -> Project:
        self._require_project(project_id)
        self._graph.invoke(
            Command(resume={"answers": answers}),
            config=self._config(project_id),
        )
        return self._require_project(project_id)

    def approve_problem_frame(self, project_id: UUID) -> Project:
        self._require_project(project_id)
        self._graph.invoke(
            Command(resume={"approved": True}),
            config=self._config(project_id),
        )
        return self._require_project(project_id)

    def request_problem_frame_revision(
        self, project_id: UUID, feedback: str
    ) -> Project:
        self._require_project(project_id)
        self._graph.invoke(
            Command(resume={"approved": False, "feedback": feedback}),
            config=self._config(project_id),
        )
        return self._require_project(project_id)

    def edit_problem_frame(
        self, project_id: UUID, content: ProblemFrameContent
    ) -> Project:
        project = self._require_project(project_id).edit_problem_frame(content)
        self._store.save(project)
        return project

    def get(self, project_id: UUID) -> Project | None:
        return self._store.get(project_id)

    def list(self) -> list[Project]:
        return self._store.list()

    def _identify_gaps(self, state: ProjectGraphState) -> ProjectGraphState:
        project_id = UUID(state["project_id"])
        intake = ProjectIntake.model_validate(state["intake"])
        questions = self._framer.identify_gaps(intake)
        project = self._require_project(project_id).with_clarification_questions(questions)
        self._store.save(project)
        return {
            "clarification_questions": [
                question.model_dump(mode="json") for question in questions
            ],
            "stage": project.stage.value,
        }

    def _collect_clarifications(self, state: ProjectGraphState) -> ProjectGraphState:
        submission = interrupt(
            {
                "kind": "clarification_required",
                "project_id": state["project_id"],
                "questions": state["clarification_questions"],
            }
        )
        answers = submission.get("answers", {})
        project_id = UUID(state["project_id"])
        project = self._require_project(project_id).with_clarification_answers(answers)
        self._store.save(project)
        return {"clarification_answers": answers}

    def _frame_problem(self, state: ProjectGraphState) -> ProjectGraphState:
        project_id = UUID(state["project_id"])
        project = self._require_project(project_id)
        problem_frame = self._framer.frame(
            project.intake,
            project.clarification_answers,
        )
        project = project.with_problem_frame(problem_frame, "初始生成")
        self._store.save(project)
        return {
            "problem_frame": problem_frame.model_dump(mode="json"),
            "stage": project.stage.value,
        }

    def _review_problem_frame(self, state: ProjectGraphState) -> ProjectGraphState:
        project = self._require_project(UUID(state["project_id"]))
        decision = interrupt(
            {
                "kind": "problem_frame_review",
                "project_id": state["project_id"],
                "problem_frame": (
                    project.problem_frame.model_dump(mode="json")
                    if project.problem_frame
                    else state.get("problem_frame")
                ),
                "version": project.problem_frame_version,
            }
        )
        return {"approval": decision}

    @staticmethod
    def _route_review(state: ProjectGraphState) -> Literal["approve", "revise"]:
        return "approve" if state["approval"].get("approved") else "revise"

    def _revise_problem_frame(self, state: ProjectGraphState) -> ProjectGraphState:
        project_id = UUID(state["project_id"])
        feedback = str(state["approval"].get("feedback", "")).strip()
        if not feedback:
            raise ValueError("Revision feedback is required")
        project = self._require_project(project_id).record_revision_request(feedback)
        self._store.save(project)
        problem_frame = self._framer.frame(
            project.intake,
            project.clarification_answers,
            revision_feedback=feedback,
        )
        project = project.with_problem_frame(problem_frame, f"根据反馈重新生成：{feedback}")
        self._store.save(project)
        return {
            "problem_frame": problem_frame.model_dump(mode="json"),
            "stage": project.stage.value,
        }

    def _approve_problem_frame(self, state: ProjectGraphState) -> ProjectGraphState:
        project_id = UUID(state["project_id"])
        project = self._require_project(project_id).approve_problem_frame()
        self._store.save(project)
        return {"stage": project.stage.value}

    def _require_project(self, project_id: UUID) -> Project:
        project = self._store.get(project_id)
        if project is None:
            raise KeyError(f"Project {project_id} not found")
        return project

    @staticmethod
    def _config(project_id: UUID) -> dict[str, dict[str, str]]:
        return {"configurable": {"thread_id": str(project_id)}}

