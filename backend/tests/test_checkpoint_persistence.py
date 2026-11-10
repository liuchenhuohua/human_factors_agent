import sqlite3
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver

from app.adapters.problem_framer import RuleBasedProblemFramer
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.domain.project import ProjectIntake, ProjectStage
from app.workflows.project_workflow import ProjectWorkflow


def test_workflow_resumes_after_process_restart(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    project_db = tmp_path / "projects.db"
    checkpoint_db = tmp_path / "checkpoints.sqlite"
    store = SQLiteProjectStore(project_db)

    first_connection = sqlite3.connect(checkpoint_db, check_same_thread=False)
    first_workflow = ProjectWorkflow(
        RuleBasedProblemFramer(), store, SqliteSaver(first_connection)
    )
    project = first_workflow.start(
        ProjectIntake(
            name="重启恢复测试",
            pain_point="复杂界面导致操作错误率持续升高",
            population="设备操作员",
            context="控制室日常任务",
        )
    )
    first_connection.close()

    second_connection = sqlite3.connect(checkpoint_db, check_same_thread=False)
    second_workflow = ProjectWorkflow(
        RuleBasedProblemFramer(), store, SqliteSaver(second_connection)
    )
    framed = second_workflow.submit_clarifications(project.id, clarification_answers)
    second_connection.close()

    third_connection = sqlite3.connect(checkpoint_db, check_same_thread=False)
    third_workflow = ProjectWorkflow(
        RuleBasedProblemFramer(), store, SqliteSaver(third_connection)
    )
    approved = third_workflow.approve_problem_frame(project.id)
    third_connection.close()

    assert framed.stage is ProjectStage.PROBLEM_FRAME_REVIEW
    assert approved.stage is ProjectStage.PROBLEM_FRAME_APPROVED

