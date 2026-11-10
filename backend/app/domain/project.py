from datetime import datetime, timezone
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ProjectStage(StrEnum):
    INTAKE = "intake"
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


class ProblemFrame(BaseModel):
    research_question: str
    human_factors_constructs: list[str]
    candidate_outcomes: list[str]
    assumptions: list[str]
    uncertainties: list[str]


class Project(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    intake: ProjectIntake
    stage: ProjectStage = ProjectStage.INTAKE
    problem_frame: ProblemFrame | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def with_problem_frame(self, problem_frame: ProblemFrame) -> "Project":
        return self.model_copy(
            update={
                "problem_frame": problem_frame,
                "stage": ProjectStage.PROBLEM_FRAME_REVIEW,
                "updated_at": datetime.now(timezone.utc),
            }
        )

    def approve_problem_frame(self) -> "Project":
        if self.stage is not ProjectStage.PROBLEM_FRAME_REVIEW:
            raise ValueError("Only a problem frame awaiting review can be approved")
        return self.model_copy(
            update={
                "stage": ProjectStage.PROBLEM_FRAME_APPROVED,
                "updated_at": datetime.now(timezone.utc),
            }
        )

