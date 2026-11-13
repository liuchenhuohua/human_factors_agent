import hashlib
from uuid import UUID

from app.domain.evidence import EvidenceSynthesis, ReviewStatus
from app.domain.evidence_ports import EvidenceStore
from app.domain.experiment import (
    ExperimentDesignType,
    ExperimentPlan,
    ExperimentPlanContent,
    ExperimentPlanReviewRequest,
    ExperimentStatus,
)
from app.domain.experiment_ports import ExperimentDesigner, ExperimentStore
from app.domain.ports import ProjectStore
from app.domain.project import Project, ProjectStage
class ExperimentWorkflow:
    """Own evidence-gated experiment drafting, validation and human approval."""

    def __init__(
        self,
        designer: ExperimentDesigner,
        project_store: ProjectStore,
        evidence_store: EvidenceStore,
        experiment_store: ExperimentStore,
    ) -> None:
        self._designer = designer
        self._project_store = project_store
        self._evidence_store = evidence_store
        self._experiment_store = experiment_store

    def start(self, project_id: UUID) -> ExperimentPlan:
        project, synthesis = self._require_inputs(project_id)
        synthesis_hash = self._synthesis_hash(synthesis)
        existing = self._experiment_store.get_by_project(project_id)
        if (
            existing is not None
            and existing.status is not ExperimentStatus.STALE
            and existing.source_synthesis_hash == synthesis_hash
        ):
            return existing
        plan = self._designer.design(project, synthesis, synthesis_hash)
        self._validate_evidence_references(plan, synthesis)
        self._experiment_store.save(plan)
        return plan

    def get(self, project_id: UUID) -> ExperimentPlan | None:
        plan = self._experiment_store.get_by_project(project_id)
        if plan is None:
            return None
        review = self._evidence_store.get_by_project(project_id)
        synthesis = review.synthesis if review else None
        if (
            synthesis is None
            or synthesis.status is not ReviewStatus.APPROVED
            or synthesis.id != plan.source_synthesis_id
            or self._synthesis_hash(synthesis) != plan.source_synthesis_hash
        ):
            plan = plan.mark_stale()
            self._experiment_store.save(plan)
        return plan

    def review(
        self,
        project_id: UUID,
        request: ExperimentPlanReviewRequest,
    ) -> ExperimentPlan:
        plan = self._experiment_store.get_by_project(project_id)
        if plan is None:
            raise KeyError(f"Experiment plan for project {project_id} not found")
        _, synthesis = self._require_inputs(project_id)
        if (
            plan.source_synthesis_id != synthesis.id
            or plan.source_synthesis_hash != self._synthesis_hash(synthesis)
        ):
            stale = plan.mark_stale()
            self._experiment_store.save(stale)
            raise ValueError("Evidence synthesis changed; regenerate the experiment plan")
        self._validate_evidence_references(request.content, synthesis)
        if request.status is ExperimentStatus.APPROVED:
            self._validate_approval_readiness(request.content)
        plan = plan.review(request)
        self._experiment_store.save(plan)
        return plan

    def _require_inputs(self, project_id: UUID) -> tuple[Project, EvidenceSynthesis]:
        project = self._project_store.get(project_id)
        if project is None:
            raise KeyError(f"Project {project_id} not found")
        if project.stage is not ProjectStage.PROBLEM_FRAME_APPROVED:
            raise ValueError("Problem frame must be approved before experiment design")
        review = self._evidence_store.get_by_project(project_id)
        if review is None or review.synthesis is None:
            raise ValueError("An approved evidence synthesis is required")
        if review.synthesis.status is not ReviewStatus.APPROVED:
            raise ValueError("Evidence synthesis must be approved before experiment design")
        return project, review.synthesis

    @staticmethod
    def _validate_evidence_references(
        content: ExperimentPlanContent,
        synthesis: EvidenceSynthesis,
    ) -> None:
        allowed = {row.evidence_item_id for row in synthesis.matrix}
        reference_sets = [
            *(hypothesis.evidence_item_ids for hypothesis in content.hypotheses),
            *(variable.evidence_item_ids for variable in content.variables),
            *(
                decision.evidence_item_ids
                for decision in content.evidence_grounded_decisions
            ),
        ]
        if any(not set(references).issubset(allowed) for references in reference_sets):
            raise ValueError("Experiment plan references evidence outside the approved synthesis")

    @staticmethod
    def _validate_approval_readiness(content: ExperimentPlanContent) -> None:
        if content.design_type is ExperimentDesignType.UNDECIDED:
            raise ValueError("Choose an experiment design type before approval")
        planning = content.sample_size_planning
        if any(
            value is None
            for value in [
                planning.effect_size_metric,
                planning.expected_effect_size,
                planning.alpha,
                planning.target_power,
            ]
        ):
            raise ValueError(
                "Effect-size metric, expected effect, alpha and target power are required"
            )

    @staticmethod
    def _synthesis_hash(synthesis: EvidenceSynthesis) -> str:
        payload = synthesis.model_dump_json(exclude_none=False)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
