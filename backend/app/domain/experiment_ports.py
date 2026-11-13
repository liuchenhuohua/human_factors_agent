from typing import Protocol
from uuid import UUID

from app.domain.evidence import EvidenceSynthesis
from app.domain.experiment import ExperimentPlan
from app.domain.project import Project


class ExperimentDesignError(RuntimeError):
    pass


class ExperimentDesigner(Protocol):
    def design(
        self,
        project: Project,
        synthesis: EvidenceSynthesis,
        synthesis_hash: str,
    ) -> ExperimentPlan: ...


class ExperimentStore(Protocol):
    def save(self, plan: ExperimentPlan) -> None: ...

    def get_by_project(self, project_id: UUID) -> ExperimentPlan | None: ...
