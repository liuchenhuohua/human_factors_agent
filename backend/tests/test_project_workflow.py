from app.domain.project import ProjectIntake, ProjectStage
from app.workflows.project_workflow import ProjectWorkflow


def test_workflow_pauses_for_review_and_resumes_on_approval(
    workflow: ProjectWorkflow,
) -> None:
    project = workflow.start(
        ProjectIntake(
            name="软件可用性研究",
            pain_point="新操作界面导致用户完成任务的效率下降",
            population="一线设备操作员",
            context="设备控制软件的日常操作",
        )
    )

    assert project.stage is ProjectStage.PROBLEM_FRAME_REVIEW
    assert project.problem_frame is not None
    assert "可用性" in project.problem_frame.human_factors_constructs

    approved = workflow.approve_problem_frame(project.id)

    assert approved.stage is ProjectStage.PROBLEM_FRAME_APPROVED

