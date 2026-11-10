from typing import Protocol
from uuid import UUID

from app.domain.project import ClarificationQuestion, ProblemFrame, Project, ProjectIntake


class ProblemFramingError(RuntimeError):
    """Raised when a framing adapter cannot produce a valid artifact."""


class ProblemFramer(Protocol):
    def identify_gaps(self, intake: ProjectIntake) -> list[ClarificationQuestion]: ...

    def frame(
        self,
        intake: ProjectIntake,
        clarification_answers: dict[str, str],
        revision_feedback: str | None = None,
    ) -> ProblemFrame: ...


class ProjectStore(Protocol):
    def save(self, project: Project) -> None: ...

    def get(self, project_id: UUID) -> Project | None: ...

    def list(self) -> list[Project]: ...

