from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.evidence_planner import RuleBasedEvidencePlanner
from app.adapters.sqlite_evidence_store import SQLiteEvidenceStore
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.adapters.evidence_extractor import RuleBasedEvidenceExtractor
from app.domain.evidence import EvidenceItemContent, LiteratureCandidate
from app.transport.evidence_http import create_evidence_router
from app.workflows.evidence_workflow import EvidenceWorkflow
from tests.test_evidence_workflow import (
    FakeDocumentStorage,
    FakeLiteratureSearch,
    FakePdfTextExtractor,
    approved_project,
)


def test_evidence_http_flow(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    project_store = SQLiteProjectStore(tmp_path / "http-evidence.db")
    evidence_store = SQLiteEvidenceStore(tmp_path / "http-evidence.db")
    project = approved_project(project_store, clarification_answers)
    workflow = EvidenceWorkflow(
        RuleBasedEvidencePlanner(),
        FakeLiteratureSearch(),
        project_store,
        evidence_store,
        FakeDocumentStorage(),
        FakePdfTextExtractor(),
        RuleBasedEvidenceExtractor(),
    )
    app = FastAPI()
    app.include_router(create_evidence_router(workflow), prefix="/api")
    client = TestClient(app)

    started = client.post(f"/api/projects/{project.id}/evidence")
    assert started.status_code == 200
    review = started.json()
    assert review["stage"] == "search_plan_review"

    searched = client.post(
        f"/api/projects/{project.id}/evidence/search-plan/approve",
        json={
            key: value
            for key, value in review["search_plan"].items()
            if key != "generation"
        },
    )
    assert searched.status_code == 200
    candidate = LiteratureCandidate.model_validate(searched.json()["candidates"][0])

    screened = client.post(
        f"/api/projects/{project.id}/evidence/candidates/{candidate.id}/screen",
        json={
            "status": "included",
            "reason": "研究构念、任务场景和结果指标均直接相关",
        },
    )
    assert screened.status_code == 200
    assert screened.json()["candidates"][0]["screening_status"] == "included"

    uploaded = client.post(
        f"/api/projects/{project.id}/evidence/candidates/{candidate.id}/document",
        files={"file": ("study.pdf", b"%PDF-1.7 test fixture", "application/pdf")},
    )
    assert uploaded.status_code == 200
    payload = uploaded.json()
    assert payload["documents"][0]["filename"] == "study.pdf"
    item = payload["evidence_items"][0]
    assert item["sample_size"] == 24

    content = {
        key: item[key]
        for key in EvidenceItemContent.model_fields
    }
    approved = client.put(
        f"/api/projects/{project.id}/evidence/evidence-items/{item['id']}",
        json={
            "content": content,
            "status": "approved",
            "note": "已逐页核验提取内容",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["evidence_items"][0]["status"] == "approved"
