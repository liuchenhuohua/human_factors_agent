from pathlib import Path

from app.adapters.evidence_planner import RuleBasedEvidencePlanner
from app.adapters.problem_framer import RuleBasedProblemFramer
from app.adapters.sqlite_evidence_store import SQLiteEvidenceStore
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.domain.evidence import (
    EvidenceStage,
    LiteratureCandidate,
    ScreeningRequest,
    ScreeningStatus,
)
from app.domain.project import ProjectIntake
from app.workflows.evidence_workflow import EvidenceWorkflow
from app.workflows.project_workflow import ProjectWorkflow


class FakeLiteratureSearch:
    def search(self, _plan):
        return [
            LiteratureCandidate(
                source="test",
                source_id="10.1/first",
                doi="10.1/first",
                title="Cognitive workload and task error",
                authors=["Ada Liu"],
                publication_year=2024,
                venue="Human Factors",
                url="https://doi.org/10.1/first",
                work_type="journal-article",
            ),
            LiteratureCandidate(
                source="test",
                source_id="10.1/second",
                doi="10.1/second",
                title="Interface usability in control rooms",
                authors=["Ming Chen"],
                publication_year=2022,
                venue="Ergonomics",
                url="https://doi.org/10.1/second",
                work_type="journal-article",
            ),
        ]


def approved_project(store: SQLiteProjectStore, answers: dict[str, str]):
    workflow = ProjectWorkflow(RuleBasedProblemFramer(), store)
    project = workflow.start(
        ProjectIntake(
            name="认知负荷研究",
            pain_point="复杂界面导致操作员认知负荷升高且容易出错",
            population="控制室操作员",
            context="日常监控和告警处置任务",
        )
    )
    workflow.submit_clarifications(project.id, answers)
    return workflow.approve_problem_frame(project.id)


def test_evidence_workflow_plans_searches_and_screens(
    tmp_path: Path,
    clarification_answers: dict[str, str],
) -> None:
    project_store = SQLiteProjectStore(tmp_path / "research.db")
    evidence_store = SQLiteEvidenceStore(tmp_path / "research.db")
    project = approved_project(project_store, clarification_answers)
    workflow = EvidenceWorkflow(
        RuleBasedEvidencePlanner(),
        FakeLiteratureSearch(),
        project_store,
        evidence_store,
    )

    review = workflow.start(project.id)
    assert review.stage is EvidenceStage.SEARCH_PLAN_REVIEW
    assert "cognitive workload" in review.search_plan.query

    review = workflow.approve_search_plan(project.id, review.search_plan)
    assert review.stage is EvidenceStage.SCREENING
    assert len(review.candidates) == 2

    candidate = review.candidates[0]
    review = workflow.screen_candidate(
        project.id,
        candidate.id,
        ScreeningRequest(
            status=ScreeningStatus.INCLUDED,
            reason="研究构念和任务绩效指标与当前问题直接相关",
        ),
    )

    assert review.candidates[0].screening_status is ScreeningStatus.INCLUDED
    assert review.candidates[0].screening_reason is not None
