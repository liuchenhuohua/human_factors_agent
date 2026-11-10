from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectStage(StrEnum):
    INTAKE = "intake"
    CLARIFICATION_REQUIRED = "clarification_required"
    PROBLEM_FRAME_REVIEW = "problem_frame_review"
    PROBLEM_FRAME_APPROVED = "problem_frame_approved"


class ProjectIntake(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    pain_point: str = Field(min_length=10, max_length=4000)
    population: str = Field(min_length=2, max_length=500)
    context: str = Field(min_length=2, max_length=1000)
    constraints: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("name", "pain_point", "population", "context")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ClarificationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]{1,40}$")
    prompt: str = Field(min_length=5, max_length=500)
    rationale: str = Field(min_length=5, max_length=500)


class ClarificationQuestionSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[ClarificationQuestion] = Field(min_length=3, max_length=5)


class ClarificationSubmission(BaseModel):
    answers: dict[str, str]

    @field_validator("answers")
    @classmethod
    def validate_answers(cls, answers: dict[str, str]) -> dict[str, str]:
        normalized = {key: value.strip() for key, value in answers.items() if value.strip()}
        if not normalized:
            raise ValueError("At least one clarification answer is required")
        return normalized


class GenerationMetadata(BaseModel):
    generator: str
    model: str | None
    prompt_version: str
    generated_at: datetime = Field(default_factory=utc_now)


class ProblemFrameContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_question: str = Field(min_length=10, max_length=2000)
    human_factors_constructs: list[str] = Field(min_length=1, max_length=12)
    candidate_outcomes: list[str] = Field(min_length=1, max_length=12)
    assumptions: list[str] = Field(min_length=1, max_length=12)
    uncertainties: list[str] = Field(min_length=1, max_length=12)


class ProblemFrame(ProblemFrameContent):
    generation: GenerationMetadata


class ProblemFrameVersion(BaseModel):
    version: int = Field(ge=1)
    frame: ProblemFrame
    change_reason: str
    created_at: datetime = Field(default_factory=utc_now)


class ReviewAction(StrEnum):
    EDITED = "edited"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"


class ReviewEvent(BaseModel):
    action: ReviewAction
    problem_frame_version: int
    note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class RevisionRequest(BaseModel):
    feedback: str = Field(min_length=3, max_length=2000)

    @field_validator("feedback")
    @classmethod
    def strip_feedback(cls, value: str) -> str:
        return value.strip()


class Project(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    intake: ProjectIntake
    stage: ProjectStage = ProjectStage.INTAKE
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    clarification_answers: dict[str, str] = Field(default_factory=dict)
    problem_frame: ProblemFrame | None = None
    problem_frame_version: int = 0
    problem_frame_history: list[ProblemFrameVersion] = Field(default_factory=list)
    review_history: list[ReviewEvent] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def with_clarification_questions(
        self, questions: list[ClarificationQuestion]
    ) -> "Project":
        return self.model_copy(
            update={
                "clarification_questions": questions,
                "stage": ProjectStage.CLARIFICATION_REQUIRED,
                "updated_at": utc_now(),
            }
        )

    def with_clarification_answers(self, answers: dict[str, str]) -> "Project":
        required_ids = {question.id for question in self.clarification_questions}
        missing = required_ids - answers.keys()
        if missing:
            raise ValueError(f"Missing clarification answers: {', '.join(sorted(missing))}")
        return self.model_copy(
            update={"clarification_answers": answers, "updated_at": utc_now()}
        )

    def with_problem_frame(
        self, problem_frame: ProblemFrame, change_reason: str
    ) -> "Project":
        version = self.problem_frame_version + 1
        version_record = ProblemFrameVersion(
            version=version,
            frame=problem_frame,
            change_reason=change_reason,
        )
        return self.model_copy(
            update={
                "problem_frame": problem_frame,
                "problem_frame_version": version,
                "problem_frame_history": [*self.problem_frame_history, version_record],
                "stage": ProjectStage.PROBLEM_FRAME_REVIEW,
                "updated_at": utc_now(),
            }
        )

    def edit_problem_frame(self, content: ProblemFrameContent) -> "Project":
        if self.stage is not ProjectStage.PROBLEM_FRAME_REVIEW:
            raise ValueError("Only a problem frame awaiting review can be edited")
        frame = ProblemFrame(
            **content.model_dump(),
            generation=GenerationMetadata(
                generator="human",
                model=None,
                prompt_version="manual-edit",
            ),
        )
        updated = self.with_problem_frame(frame, "人工编辑")
        event = ReviewEvent(
            action=ReviewAction.EDITED,
            problem_frame_version=updated.problem_frame_version,
        )
        return updated.model_copy(update={"review_history": [*updated.review_history, event]})

    def record_revision_request(self, feedback: str) -> "Project":
        if self.stage is not ProjectStage.PROBLEM_FRAME_REVIEW:
            raise ValueError("Only a problem frame awaiting review can be revised")
        event = ReviewEvent(
            action=ReviewAction.REVISION_REQUESTED,
            problem_frame_version=self.problem_frame_version,
            note=feedback,
        )
        return self.model_copy(
            update={
                "review_history": [*self.review_history, event],
                "updated_at": utc_now(),
            }
        )

    def approve_problem_frame(self) -> "Project":
        if self.stage is not ProjectStage.PROBLEM_FRAME_REVIEW:
            raise ValueError("Only a problem frame awaiting review can be approved")
        event = ReviewEvent(
            action=ReviewAction.APPROVED,
            problem_frame_version=self.problem_frame_version,
        )
        return self.model_copy(
            update={
                "stage": ProjectStage.PROBLEM_FRAME_APPROVED,
                "review_history": [*self.review_history, event],
                "updated_at": utc_now(),
            }
        )

