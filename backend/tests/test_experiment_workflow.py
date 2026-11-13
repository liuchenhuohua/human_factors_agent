from pathlib import Path
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.experiment_designer import RuleBasedExperimentDesigner
from app.adapters.sqlite_evidence_store import SQLiteEvidenceStore
from app.adapters.sqlite_experiment_store import SQLiteExperimentStore
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.domain.evidence import (
    AppraisalConfidence,
    EvidenceMatrixRow,
    EvidenceReview,
    EvidenceSynthesis,
    ReviewStatus,
    SearchPlan,
)
from app.domain.experiment import (
    ExperimentDesignType,
    ExperimentPlanContent,
    ExperimentPlanReviewRequest,
    ExperimentStatus,
)
from app.domain.project import GenerationMetadata
from app.transport.experiment_http import create_experiment_router
from app.workflows.experiment_workflow import ExperimentWorkflow
from tests.test_evidence_workflow import approved_project


def approved_synthesis_review(project_id) -> EvidenceReview:
    evidence_item_id = uuid4()
    candidate_id = uuid4()
    synthesis = EvidenceSynthesis(
        matrix=[
            EvidenceMatrixRow(
                evidence_item_id=evidence_item_id,
                candidate_id=candidate_id,
                citation="Cognitive workload experiment (2024)",
                population_and_context="控制室操作员；告警处置任务",
                design_and_sample="受控实验；样本量 n=48",
                exposures_or_interventions=["告警界面复杂度"],
                outcomes_and_measures=["认知负荷", "任务错误率", "NASA-TLX"],
                findings_and_effects=["复杂界面条件下认知负荷更高"],
                limitations=["单中心研究"],
                appraisal_confidence=AppraisalConfidence.MODERATE,
            )
        ],
        consistent_findings=[],
        conflicting_findings=[],
        evidence_gaps=["缺少不同经验水平操作员的比较"],
        transferability_notes=["目标场景与研究场景相近"],
        cautions=["仅一项研究，无法判断跨研究一致性"],
        status=ReviewStatus.APPROVED,
        generation=GenerationMetadata(
            generator="human",
            model=None,
            prompt_version="test-synthesis",
        ),
    )
    return EvidenceReview(
        project_id=project_id,
        search_plan=SearchPlan(
            query="cognitive workload alarm interface",
            keywords=["cognitive workload", "alarm", "interface"],
            inclusion_criteria=["Human factors study"],
            exclusion_criteria=["Unrelated population"],
            from_year=2015,
            until_year=2026,
            max_results=20,
            generation=GenerationMetadata(
                generator="human",
                model=None,
                prompt_version="test-plan",
            ),
        ),
        synthesis=synthesis,
    )


def build_workflow(tmp_path: Path, clarification_answers: dict[str, str]):
    project_store = SQLiteProjectStore(tmp_path / "experiment.db")
    evidence_store = SQLiteEvidenceStore(tmp_path / "experiment.db")
    experiment_store = SQLiteExperimentStore(tmp_path / "experiment.db")
    project = approved_project(project_store, clarification_answers)
    evidence_store.save(approved_synthesis_review(project.id))
    workflow = ExperimentWorkflow(
        RuleBasedExperimentDesigner(),
        project_store,
        evidence_store,
        experiment_store,
    )
    return workflow, evidence_store, project


def ready_for_approval(plan) -> ExperimentPlanContent:
    content = ExperimentPlanContent.model_validate(
        plan.model_dump(include=set(ExperimentPlanContent.model_fields))
    )
    planning = content.sample_size_planning.model_copy(
        update={
            "planned_primary_test": "配对样本 t 检验",
            "effect_size_metric": "Cohen's dz",
            "expected_effect_size": 0.5,
            "effect_size_basis": "依据预实验或最小实际重要差异，待确定性计算复核",
            "alpha": 0.05,
            "target_power": 0.8,
            "attrition_allowance": 0.1,
        }
    )
    return content.model_copy(
        update={
            "design_type": ExperimentDesignType.WITHIN_SUBJECTS,
            "sample_size_planning": planning,
        }
    )


def test_experiment_workflow_requires_review_and_detects_stale_synthesis(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    workflow, evidence_store, project = build_workflow(
        tmp_path,
        clarification_answers,
    )

    plan = workflow.start(project.id)
    assert plan.status is ExperimentStatus.PENDING_REVIEW
    assert plan.design_type is ExperimentDesignType.UNDECIDED
    assert plan.sample_size_planning.expected_effect_size is None

    content = ExperimentPlanContent.model_validate(
        plan.model_dump(include=set(ExperimentPlanContent.model_fields))
    )
    invalid_hypothesis = content.hypotheses[0].model_copy(
        update={"evidence_item_ids": [uuid4()]}
    )
    invalid_references = content.model_copy(
        update={"hypotheses": [invalid_hypothesis]}
    )
    with pytest.raises(ValueError, match="outside the approved synthesis"):
        workflow.review(
            project.id,
            ExperimentPlanReviewRequest(
                content=invalid_references,
                status=ExperimentStatus.NEEDS_REVISION,
                note="测试无效证据引用",
            ),
        )
    with pytest.raises(ValueError, match="design type"):
        workflow.review(
            project.id,
            ExperimentPlanReviewRequest(
                content=content,
                status=ExperimentStatus.APPROVED,
            ),
        )

    plan = workflow.review(
        project.id,
        ExperimentPlanReviewRequest(
            content=ready_for_approval(plan),
            status=ExperimentStatus.APPROVED,
            note="已核验设计类型、主要结局与功效分析输入",
        ),
    )
    assert plan.status is ExperimentStatus.APPROVED
    assert plan.generation.generator == "human"

    review = evidence_store.get_by_project(project.id)
    assert review is not None and review.synthesis is not None
    changed = review.synthesis.model_copy(
        update={"cautions": [*review.synthesis.cautions, "新增证据限制"]}
    )
    evidence_store.save(review.model_copy(update={"synthesis": changed}))
    assert workflow.get(project.id).status is ExperimentStatus.STALE


def test_experiment_http_flow(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    workflow, _, project = build_workflow(tmp_path, clarification_answers)
    app = FastAPI()
    app.include_router(create_experiment_router(workflow), prefix="/api")
    client = TestClient(app)

    started = client.post(f"/api/projects/{project.id}/experiment-plan")
    assert started.status_code == 200
    plan = started.json()
    content = {
        key: plan[key]
        for key in ExperimentPlanContent.model_fields
    }
    content["design_type"] = "within_subjects"
    content["sample_size_planning"].update(
        {
            "planned_primary_test": "配对样本 t 检验",
            "effect_size_metric": "Cohen's dz",
            "expected_effect_size": 0.5,
            "alpha": 0.05,
            "target_power": 0.8,
            "attrition_allowance": 0.1,
        }
    )
    approved = client.put(
        f"/api/projects/{project.id}/experiment-plan",
        json={
            "content": content,
            "status": "approved",
            "note": "已完成实验设计人工复核",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
