from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.evidence_planner import RuleBasedEvidencePlanner
from app.adapters.sqlite_evidence_store import SQLiteEvidenceStore
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.domain.evidence import LiteratureCandidate
from app.transport.evidence_http import create_evidence_router
from app.workflows.evidence_workflow import EvidenceWorkflow
from tests.test_evidence_workflow import FakeLiteratureSearch, approved_project


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
            "status": "excluded",
            "reason": "研究对象与当前目标人群不匹配",
        },
    )
    assert screened.status_code == 200
    assert screened.json()["candidates"][0]["screening_status"] == "excluded"
