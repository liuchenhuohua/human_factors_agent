from app.adapters.problem_framer import RuleBasedProblemFramer
from app.domain.project import ProjectIntake


def test_identifies_gaps_and_frames_problem() -> None:
    framer = RuleBasedProblemFramer()
    intake = ProjectIntake(
        name="夜班装配错误研究",
        pain_point="夜班装配人员的操作错误率明显上升",
        population="装配操作员",
        context="夜间装配工位",
    )

    questions = framer.identify_gaps(intake)
    frame = framer.frame(
        intake,
        {
            "baseline_severity": "每周约 8 次",
            "suspected_factors": "夜班疲劳",
            "decision_goal": "调整排班",
        },
    )

    assert len(questions) == 3
    assert "疲劳与昼夜节律" in frame.human_factors_constructs
    assert "人的可靠性" in frame.human_factors_constructs
    assert "错误率" in frame.candidate_outcomes
    assert frame.generation.generator == "rule_based"
    assert any("因果" in uncertainty for uncertainty in frame.uncertainties)

