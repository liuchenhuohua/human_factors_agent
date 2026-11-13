from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.data_contract_builder import (
    CsvDataTemplateRenderer,
    RuleBasedDataContractBuilder,
)
from app.adapters.experiment_designer import RuleBasedExperimentDesigner
from app.adapters.power_calculator import StatsmodelsPowerCalculator
from app.adapters.sqlite_evidence_store import SQLiteEvidenceStore
from app.adapters.sqlite_experiment_store import SQLiteExperimentStore
from app.adapters.sqlite_preparation_store import SQLitePreparationStore
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.domain.experiment import ExperimentPlanReviewRequest, ExperimentStatus
from app.domain.preparation import (
    DataContractContent,
    DataContractReviewRequest,
    PowerAnalysisRequest,
    PowerAnalysisReviewRequest,
    PowerTestType,
    PreparationStatus,
)
from app.transport.preparation_http import create_preparation_router
from app.workflows.experiment_workflow import ExperimentWorkflow
from app.workflows.preparation_workflow import PreparationWorkflow
from tests.test_evidence_workflow import approved_project
from tests.test_experiment_workflow import (
    approved_synthesis_review,
    ready_for_approval,
)


def build_preparation_workflow(
    tmp_path: Path,
    clarification_answers: dict[str, str],
):
    database_path = tmp_path / "preparation.db"
    project_store = SQLiteProjectStore(database_path)
    evidence_store = SQLiteEvidenceStore(database_path)
    experiment_store = SQLiteExperimentStore(database_path)
    preparation_store = SQLitePreparationStore(database_path)
    project = approved_project(project_store, clarification_answers)
    evidence_store.save(approved_synthesis_review(project.id))
    experiment_workflow = ExperimentWorkflow(
        RuleBasedExperimentDesigner(),
        project_store,
        evidence_store,
        experiment_store,
    )
    draft = experiment_workflow.start(project.id)
    plan = experiment_workflow.review(
        project.id,
        ExperimentPlanReviewRequest(
            content=ready_for_approval(draft),
            status=ExperimentStatus.APPROVED,
            note="批准用于功效分析和数据契约测试",
        ),
    )
    workflow = PreparationWorkflow(
        StatsmodelsPowerCalculator(),
        RuleBasedDataContractBuilder(),
        CsvDataTemplateRenderer(),
        experiment_store,
        preparation_store,
    )
    return workflow, experiment_store, project, plan


@pytest.mark.parametrize(
    ("test_type", "effect_size", "groups", "expected_total"),
    [
        (PowerTestType.INDEPENDENT_T, 0.5, 2, 128),
        (PowerTestType.PAIRED_T, 0.5, 2, 34),
        (PowerTestType.ONE_WAY_ANOVA, 0.25, 3, 159),
        (PowerTestType.CORRELATION, 0.3, 2, 85),
    ],
)
def test_supported_power_calculations_are_deterministic(
    tmp_path: Path,
    clarification_answers: dict[str, str],
    test_type: PowerTestType,
    effect_size: float,
    groups: int,
    expected_total: int,
) -> None:
    workflow, _, project, _ = build_preparation_workflow(
        tmp_path,
        clarification_answers,
    )
    preparation = workflow.calculate_power(
        project.id,
        PowerAnalysisRequest(
            test_type=test_type,
            effect_size=effect_size,
            alpha=0.05,
            target_power=0.8,
            groups=groups,
            attrition_rate=0,
        ),
    )
    assert preparation.power_analysis is not None
    assert preparation.power_analysis.primary_result.nominal_total_n == expected_total
    assert "statsmodels" in preparation.power_analysis.package_versions


def test_smaller_one_sided_effect_uses_the_requested_direction(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    workflow, _, project, _ = build_preparation_workflow(
        tmp_path,
        clarification_answers,
    )
    preparation = workflow.calculate_power(
        project.id,
        PowerAnalysisRequest(
            test_type=PowerTestType.INDEPENDENT_T,
            effect_size=0.5,
            alpha=0.05,
            target_power=0.8,
            alternative="smaller",
        ),
    )
    assert preparation.power_analysis is not None
    assert preparation.power_analysis.primary_result.nominal_total_n == 102


def test_correlation_effect_must_be_below_one() -> None:
    with pytest.raises(ValueError, match="less than one"):
        PowerAnalysisRequest(
            test_type=PowerTestType.CORRELATION,
            effect_size=1,
            alpha=0.05,
            target_power=0.8,
        )


def test_preparation_workflow_approves_template_and_detects_stale_plan(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    workflow, experiment_store, project, plan = build_preparation_workflow(
        tmp_path,
        clarification_answers,
    )
    preparation = workflow.calculate_power(
        project.id,
        PowerAnalysisRequest(
            test_type=PowerTestType.PAIRED_T,
            effect_size=0.5,
            alpha=0.05,
            target_power=0.8,
            attrition_rate=0.1,
            sensitivity_effect_sizes=[0.3, 0.5, 0.7],
            sensitivity_powers=[0.8, 0.9],
        ),
    )
    assert preparation.power_analysis is not None
    assert preparation.power_analysis.primary_result.adjusted_total_n == 38
    preparation = workflow.review_power(
        project.id,
        PowerAnalysisReviewRequest(
            status=PreparationStatus.APPROVED,
            note="已核对效应量依据和检验参数",
        ),
    )
    preparation = workflow.generate_data_contract(project.id)
    assert preparation.data_contract is not None
    keys = [field.key for field in preparation.data_contract.fields]
    assert {"participant_id", "condition", "trial_index", "recorded_at"}.issubset(keys)
    assert next(
        field for field in preparation.data_contract.fields if field.key == "participant_id"
    ).sensitive
    content = DataContractContent.model_validate(
        preparation.data_contract.model_dump(
            include=set(DataContractContent.model_fields)
        )
    )
    preparation = workflow.review_data_contract(
        project.id,
        DataContractReviewRequest(
            content=content,
            status=PreparationStatus.APPROVED,
            note="已核验字段类型、编码和敏感性",
        ),
    )
    assert preparation.data_contract.status is PreparationStatus.APPROVED
    template = workflow.render_csv_template(project.id).decode("utf-8-sig")
    assert template.startswith("participant_id,condition,trial_index,recorded_at")

    experiment_store.save(plan.model_copy(update={"title": "变更后的实验方案"}))
    stale = workflow.get(project.id)
    assert stale.power_analysis.status is PreparationStatus.STALE
    assert stale.data_contract.status is PreparationStatus.STALE
    assert workflow.get(project.id).updated_at == stale.updated_at


def test_preparation_http_flow(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    workflow, _, project, _ = build_preparation_workflow(
        tmp_path,
        clarification_answers,
    )
    app = FastAPI()
    app.include_router(create_preparation_router(workflow), prefix="/api")
    client = TestClient(app)

    calculated = client.post(
        f"/api/projects/{project.id}/study-preparation/power-analysis",
        json={
            "test_type": "independent_t",
            "effect_size": 0.5,
            "alpha": 0.05,
            "target_power": 0.8,
            "alternative": "two-sided",
            "groups": 2,
            "allocation_ratio": 1,
            "attrition_rate": 0.1,
            "sensitivity_effect_sizes": [0.3, 0.5, 0.7],
            "sensitivity_powers": [0.8, 0.9],
        },
    )
    assert calculated.status_code == 200
    assert calculated.json()["power_analysis"]["primary_result"]["adjusted_total_n"] == 144

    generated = client.post(
        f"/api/projects/{project.id}/study-preparation/data-contract"
    )
    contract = generated.json()["data_contract"]
    content = {
        key: contract[key]
        for key in DataContractContent.model_fields
    }
    approved = client.put(
        f"/api/projects/{project.id}/study-preparation/data-contract",
        json={
            "content": content,
            "status": "approved",
            "note": "批准数据采集契约",
        },
    )
    assert approved.status_code == 200
    downloaded = client.get(
        f"/api/projects/{project.id}/study-preparation/template.csv"
    )
    assert downloaded.status_code == 200
    assert downloaded.headers["content-type"].startswith("text/csv")
