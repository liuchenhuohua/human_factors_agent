import os
from pathlib import Path

import pytest

os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")

from app.adapters.problem_framer import RuleBasedProblemFramer
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.workflows.project_workflow import ProjectWorkflow


@pytest.fixture
def workflow(tmp_path: Path) -> ProjectWorkflow:
    return ProjectWorkflow(
        RuleBasedProblemFramer(),
        SQLiteProjectStore(tmp_path / "test.db"),
    )


@pytest.fixture
def clarification_answers() -> dict[str, str]:
    return {
        "baseline_severity": "过去一个月每周约发生 8 次，严重时需要返工",
        "suspected_factors": "界面层级复杂、夜班疲劳和新员工经验不足",
        "decision_goal": "决定是否重设计界面并调整夜班任务安排",
    }

