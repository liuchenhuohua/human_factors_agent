from typing import Protocol
from uuid import UUID

from app.domain.experiment import ExperimentPlan
from app.domain.preparation import (
    DataContract,
    PowerAnalysis,
    PowerAnalysisRequest,
    StudyPreparation,
)


class PowerCalculationError(RuntimeError):
    pass


class PowerCalculator(Protocol):
    def calculate(
        self,
        project_id: UUID,
        plan: ExperimentPlan,
        plan_hash: str,
        request: PowerAnalysisRequest,
    ) -> PowerAnalysis: ...


class DataContractBuilder(Protocol):
    def build(self, plan: ExperimentPlan, plan_hash: str) -> DataContract: ...


class CsvTemplateRenderer(Protocol):
    def render(self, contract: DataContract) -> bytes: ...


class PreparationStore(Protocol):
    def save(self, preparation: StudyPreparation) -> None: ...

    def get(self, project_id: UUID) -> StudyPreparation | None: ...
