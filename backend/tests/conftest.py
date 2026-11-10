from pathlib import Path

import pytest

from app.adapters.problem_framer import RuleBasedProblemFramer
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.workflows.project_workflow import ProjectWorkflow


@pytest.fixture
def workflow(tmp_path: Path) -> ProjectWorkflow:
    return ProjectWorkflow(
        RuleBasedProblemFramer(),
        SQLiteProjectStore(tmp_path / "test.db"),
    )

