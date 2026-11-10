from app.domain.project import ProblemFrameContent, ProjectIntake, ProjectStage
from app.workflows.project_workflow import ProjectWorkflow


def build_intake() -> ProjectIntake:
    return ProjectIntake(
        name="软件可用性研究",
        pain_point="新操作界面导致用户完成任务的效率下降",
        population="一线设备操作员",
        context="设备控制软件的日常操作",
    )


def test_workflow_clarifies_then_pauses_for_review_and_approves(
    workflow: ProjectWorkflow,
    clarification_answers: dict[str, str],
) -> None:
    project = workflow.start(build_intake())

    assert project.stage is ProjectStage.CLARIFICATION_REQUIRED
    assert len(project.clarification_questions) == 3

    framed = workflow.submit_clarifications(project.id, clarification_answers)

    assert framed.stage is ProjectStage.PROBLEM_FRAME_REVIEW
    assert framed.problem_frame is not None
    assert framed.problem_frame_version == 1
    assert "可用性" in framed.problem_frame.human_factors_constructs

    approved = workflow.approve_problem_frame(project.id)

    assert approved.stage is ProjectStage.PROBLEM_FRAME_APPROVED
    assert approved.review_history[-1].action == "approved"


def test_problem_frame_can_be_edited_and_regenerated(
    workflow: ProjectWorkflow,
    clarification_answers: dict[str, str],
) -> None:
    project = workflow.start(build_intake())
    project = workflow.submit_clarifications(project.id, clarification_answers)
    assert project.problem_frame is not None

    edited = workflow.edit_problem_frame(
        project.id,
        ProblemFrameContent(
            research_question="夜班与日班操作员在界面任务错误率上是否存在显著差异？",
            human_factors_constructs=["可用性", "疲劳与昼夜节律"],
            candidate_outcomes=["错误率", "任务完成时间"],
            assumptions=["两组执行相同任务"],
            uncertainties=["操作经验可能构成混杂因素"],
        ),
    )
    assert edited.problem_frame_version == 2
    assert edited.problem_frame is not None
    assert edited.problem_frame.generation.generator == "human"

    revised = workflow.request_problem_frame_revision(
        project.id,
        "进一步强调不同经验水平可能造成的混杂",
    )
    assert revised.problem_frame_version == 3
    assert revised.stage is ProjectStage.PROBLEM_FRAME_REVIEW
    assert revised.review_history[-1].action == "revision_requested"

