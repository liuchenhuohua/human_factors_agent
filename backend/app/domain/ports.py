from typing import Protocol
from uuid import UUID

from app.domain.project import ProblemFrame, Project, ProjectIntake


class ProblemFramer(Protocol):
    def frame(self, intake: ProjectIntake) -> ProblemFrame: ...


class ProjectStore(Protocol):
    def save(self, project: Project) -> None: ...

    def get(self, project_id: UUID) -> Project | None: ...

    def list(self) -> list[Project]: ...

