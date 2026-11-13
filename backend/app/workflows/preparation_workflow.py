import hashlib
from uuid import UUID

from app.domain.experiment import ExperimentPlan, ExperimentStatus
from app.domain.experiment_ports import ExperimentStore
from app.domain.preparation import (
    DataContractReviewRequest,
    PowerAnalysisRequest,
    PowerAnalysisReviewRequest,
    PreparationStatus,
    StudyPreparation,
)
from app.domain.preparation_ports import (
    CsvTemplateRenderer,
    DataContractBuilder,
    PowerCalculator,
    PreparationStore,
)
from app.domain.project import utc_now


class PreparationWorkflow:
    """Own deterministic power analysis and versioned collection contracts."""

    def __init__(
        self,
        calculator: PowerCalculator,
        contract_builder: DataContractBuilder,
        template_renderer: CsvTemplateRenderer,
        experiment_store: ExperimentStore,
        preparation_store: PreparationStore,
    ) -> None:
        self._calculator = calculator
        self._contract_builder = contract_builder
        self._template_renderer = template_renderer
        self._experiment_store = experiment_store
        self._preparation_store = preparation_store

    def calculate_power(
        self,
        project_id: UUID,
        request: PowerAnalysisRequest,
    ) -> StudyPreparation:
        plan = self._require_approved_plan(project_id)
        plan_hash = self._plan_hash(plan)
        analysis = self._calculator.calculate(project_id, plan, plan_hash, request)
        preparation = self._preparation_store.get(project_id) or StudyPreparation(
            project_id=project_id
        )
        preparation = preparation.with_power_analysis(analysis)
        self._preparation_store.save(preparation)
        return preparation

    def generate_data_contract(self, project_id: UUID) -> StudyPreparation:
        plan = self._require_approved_plan(project_id)
        plan_hash = self._plan_hash(plan)
        preparation = self._preparation_store.get(project_id) or StudyPreparation(
            project_id=project_id
        )
        existing = preparation.data_contract
        if (
            existing is not None
            and existing.status not in {
                PreparationStatus.STALE,
                PreparationStatus.NEEDS_REVISION,
            }
            and existing.source_plan_hash == plan_hash
        ):
            return preparation
        contract = self._contract_builder.build(plan, plan_hash)
        preparation = preparation.with_data_contract(contract)
        self._preparation_store.save(preparation)
        return preparation

    def review_power(
        self,
        project_id: UUID,
        request: PowerAnalysisReviewRequest,
    ) -> StudyPreparation:
        plan = self._require_approved_plan(project_id)
        preparation = self._require_preparation(project_id)
        analysis = preparation.power_analysis
        if analysis is None:
            raise KeyError("Power analysis not found")
        self._require_current_source(analysis.source_plan_hash, plan)
        preparation = preparation.with_power_analysis(analysis.review(request))
        self._preparation_store.save(preparation)
        return preparation

    def review_data_contract(
        self,
        project_id: UUID,
        request: DataContractReviewRequest,
    ) -> StudyPreparation:
        plan = self._require_approved_plan(project_id)
        preparation = self._require_preparation(project_id)
        contract = preparation.data_contract
        if contract is None:
            raise KeyError("Data contract not found")
        self._require_current_source(contract.source_plan_hash, plan)
        preparation = preparation.with_data_contract(contract.review(request))
        self._preparation_store.save(preparation)
        return preparation

    def get(self, project_id: UUID) -> StudyPreparation | None:
        preparation = self._preparation_store.get(project_id)
        if preparation is None:
            return None
        plan = self._experiment_store.get_by_project(project_id)
        current_hash = (
            self._plan_hash(plan)
            if plan is not None and plan.status is ExperimentStatus.APPROVED
            else None
        )
        changed = False
        analysis = preparation.power_analysis
        if (
            analysis is not None
            and analysis.status is not PreparationStatus.STALE
            and analysis.source_plan_hash != current_hash
        ):
            analysis = analysis.mark_stale()
            changed = True
        contract = preparation.data_contract
        if (
            contract is not None
            and contract.status is not PreparationStatus.STALE
            and contract.source_plan_hash != current_hash
        ):
            contract = contract.mark_stale()
            changed = True
        if changed:
            preparation = preparation.model_copy(
                update={
                    "power_analysis": analysis,
                    "data_contract": contract,
                    "updated_at": utc_now(),
                }
            )
            self._preparation_store.save(preparation)
        return preparation

    def render_csv_template(self, project_id: UUID) -> bytes:
        plan = self._require_approved_plan(project_id)
        preparation = self._require_preparation(project_id)
        contract = preparation.data_contract
        if contract is None or contract.status is not PreparationStatus.APPROVED:
            raise ValueError("Approve the data contract before downloading a template")
        self._require_current_source(contract.source_plan_hash, plan)
        return self._template_renderer.render(contract)

    def _require_approved_plan(self, project_id: UUID) -> ExperimentPlan:
        plan = self._experiment_store.get_by_project(project_id)
        if plan is None:
            raise KeyError(f"Experiment plan for project {project_id} not found")
        if plan.status is not ExperimentStatus.APPROVED:
            raise ValueError("Experiment plan must be approved before study preparation")
        return plan

    def _require_preparation(self, project_id: UUID) -> StudyPreparation:
        preparation = self._preparation_store.get(project_id)
        if preparation is None:
            raise KeyError(f"Study preparation for project {project_id} not found")
        return preparation

    def _require_current_source(self, source_hash: str, plan: ExperimentPlan) -> None:
        if source_hash != self._plan_hash(plan):
            raise ValueError("Experiment plan changed; regenerate study preparation")

    @staticmethod
    def _plan_hash(plan: ExperimentPlan) -> str:
        return hashlib.sha256(plan.model_dump_json().encode("utf-8")).hexdigest()
