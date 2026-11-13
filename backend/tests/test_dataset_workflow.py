import csv
from io import StringIO
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.csv_dataset_validator import CsvDatasetValidator
from app.adapters.local_dataset_storage import LocalDatasetStorage
from app.adapters.sqlite_dataset_store import SQLiteDatasetStore
from app.domain.dataset import DatasetReviewRequest, DatasetStatus
from app.domain.preparation import (
    DataContractContent,
    DataContractReviewRequest,
    DataField,
    DataType,
    PreparationStatus,
)
from app.transport.dataset_http import create_dataset_router
from app.workflows.dataset_workflow import DatasetWorkflow
from tests.test_preparation_workflow import build_preparation_workflow


def build_dataset_workflow(
    tmp_path: Path,
    clarification_answers: dict[str, str],
):
    preparation_workflow, _, project, _ = build_preparation_workflow(
        tmp_path,
        clarification_answers,
    )
    preparation = preparation_workflow.generate_data_contract(project.id)
    contract = preparation.data_contract
    content = DataContractContent.model_validate(
        contract.model_dump(include=set(DataContractContent.model_fields))
    )
    preparation = preparation_workflow.review_data_contract(
        project.id,
        DataContractReviewRequest(
            content=content,
            status=PreparationStatus.APPROVED,
            note="批准用于数据质量测试",
        ),
    )
    workflow = DatasetWorkflow(
        CsvDatasetValidator(),
        LocalDatasetStorage(tmp_path / "datasets"),
        SQLiteDatasetStore(tmp_path / "preparation.db"),
        preparation_workflow,
        max_upload_bytes=1024 * 1024,
    )
    return workflow, preparation_workflow, project, preparation.data_contract


def valid_csv(fields: list[DataField], rows: int = 2) -> bytes:
    stream = StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow([field.key for field in fields])
    for row_index in range(1, rows + 1):
        values = []
        for field in fields:
            if field.key == "participant_id":
                value = f"P{row_index:03d}"
            elif field.key == "condition":
                value = field.categories[(row_index - 1) % len(field.categories)]
            elif field.key == "trial_index":
                value = "1"
            elif field.data_type is DataType.DATETIME:
                value = f"2026-11-13T10:0{row_index}:00+08:00"
            elif field.data_type is DataType.CATEGORY:
                value = field.categories[(row_index - 1) % len(field.categories)]
            elif field.data_type is DataType.INTEGER:
                value = str(row_index)
            elif field.data_type is DataType.FLOAT:
                value = str(row_index + 0.5)
            elif field.data_type is DataType.BOOLEAN:
                value = "true"
            else:
                value = f"value-{row_index}"
            values.append(value)
        writer.writerow(values)
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def test_valid_dataset_is_versioned_reviewed_and_downloadable(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    workflow, _, project, contract = build_dataset_workflow(
        tmp_path,
        clarification_answers,
    )
    source = valid_csv(contract.fields)
    registry = workflow.upload(project.id, "study.csv", "text/csv", source)
    dataset = registry.datasets[0]
    assert dataset.version == 1
    assert dataset.status is DatasetStatus.PENDING_REVIEW
    assert dataset.quality_report.valid_for_analysis
    assert dataset.quality_report.error_count == 0

    registry = workflow.review(
        project.id,
        dataset.id,
        DatasetReviewRequest(
            status=DatasetStatus.ANALYSIS_READY,
            note="已复核质量报告和原始数据",
        ),
    )
    assert registry.active_dataset_id == dataset.id
    assert registry.datasets[0].status is DatasetStatus.ANALYSIS_READY
    downloaded, content = workflow.download(project.id, dataset.id)
    assert downloaded.sha256 == dataset.sha256
    assert content == source


def test_invalid_dataset_reports_contract_and_row_errors(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    workflow, _, project, contract = build_dataset_workflow(
        tmp_path,
        clarification_answers,
    )
    source = valid_csv(contract.fields).decode("utf-8-sig")
    rows = list(csv.reader(StringIO(source)))
    dependent_index = next(
        index
        for index, field in enumerate(contract.fields)
        if field.data_type is DataType.FLOAT
    )
    rows[1][dependent_index] = "not-a-number"
    rows[2][0] = rows[1][0]
    rows[2][1] = rows[1][1]
    rows[2][2] = rows[1][2]
    rows[0].append("unexpected")
    rows[1].append("x")
    rows[2].append("x")
    stream = StringIO(newline="")
    csv.writer(stream).writerows(rows)

    registry = workflow.upload(
        project.id,
        "invalid.csv",
        "text/csv",
        stream.getvalue().encode("utf-8"),
    )
    report = registry.datasets[0].quality_report
    assert registry.datasets[0].status is DatasetStatus.VALIDATION_FAILED
    assert not report.valid_for_analysis
    assert report.duplicate_primary_key_count == 1
    assert {issue.code for issue in report.issues}.issuperset(
        {"extra_columns", "invalid_value", "duplicate_primary_key"}
    )
    with pytest.raises(ValueError, match="validation errors"):
        workflow.review(
            project.id,
            registry.datasets[0].id,
            DatasetReviewRequest(
                status=DatasetStatus.ANALYSIS_READY,
                note="不应允许批准",
            ),
        )


def test_contract_change_marks_existing_dataset_stale(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    workflow, preparation_workflow, project, contract = build_dataset_workflow(
        tmp_path,
        clarification_answers,
    )
    registry = workflow.upload(
        project.id,
        "study.csv",
        "text/csv",
        valid_csv(contract.fields),
    )
    content = DataContractContent.model_validate(
        contract.model_dump(include=set(DataContractContent.model_fields))
    ).model_copy(update={"collection_notes": [*contract.collection_notes, "新增规则"]})
    preparation_workflow.review_data_contract(
        project.id,
        DataContractReviewRequest(
            content=content,
            status=PreparationStatus.APPROVED,
            note="更新采集规则",
        ),
    )

    stale = workflow.get(project.id)
    assert stale.datasets[0].status is DatasetStatus.STALE
    assert stale.active_dataset_id is None
    assert workflow.get(project.id).updated_at == stale.updated_at


def test_dataset_http_upload_review_and_download(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    workflow, _, project, contract = build_dataset_workflow(
        tmp_path,
        clarification_answers,
    )
    app = FastAPI()
    app.include_router(create_dataset_router(workflow), prefix="/api")
    client = TestClient(app)
    source = valid_csv(contract.fields)

    uploaded = client.post(
        f"/api/projects/{project.id}/datasets",
        files={"file": ("study.csv", source, "text/csv")},
    )
    assert uploaded.status_code == 200
    dataset_id = uploaded.json()["datasets"][0]["id"]
    reviewed = client.put(
        f"/api/projects/{project.id}/datasets/{dataset_id}",
        json={"status": "analysis_ready", "note": "批准进入统计分析"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["active_dataset_id"] == dataset_id
    downloaded = client.get(
        f"/api/projects/{project.id}/datasets/{dataset_id}/source.csv"
    )
    assert downloaded.status_code == 200
    assert downloaded.content == source
    assert downloaded.headers["x-content-sha256"]
