from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.adapters.problem_framer import RuleBasedProblemFramer
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.transport.http import create_router
from app.workflows.project_workflow import ProjectWorkflow


def test_full_problem_framing_http_flow(tmp_path: Path) -> None:
    workflow = ProjectWorkflow(
        RuleBasedProblemFramer(), SQLiteProjectStore(tmp_path / "http.db")
    )
    app = FastAPI()
    app.include_router(create_router(workflow), prefix="/api")
    client = TestClient(app)

    response = client.post(
        "/api/projects",
        json={
            "name": "认知负荷研究",
            "pain_point": "复杂表单导致操作员认知负荷升高且容易出错",
            "population": "业务操作员",
            "context": "后台系统表单填写任务",
            "constraints": ["测试时间不超过 30 分钟"],
        },
    )
    assert response.status_code == 201
    project = response.json()
    assert project["stage"] == "clarification_required"

    clarification = client.post(
        f"/api/projects/{project['id']}/clarifications",
        json={
            "answers": {
                "baseline_severity": "每周约 5 次错误",
                "suspected_factors": "信息密度和操作经验",
                "decision_goal": "优化表单布局",
            }
        },
    )
    assert clarification.status_code == 200
    framed = clarification.json()
    assert framed["stage"] == "problem_frame_review"
    assert framed["problem_frame_version"] == 1

    approval = client.post(
        f"/api/projects/{project['id']}/problem-frame/approve"
    )
    assert approval.status_code == 200
    assert approval.json()["stage"] == "problem_frame_approved"

