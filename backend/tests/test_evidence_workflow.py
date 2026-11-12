import hashlib
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.adapters.evidence_extractor import RuleBasedEvidenceExtractor
from app.adapters.evidence_synthesis import (
    RuleBasedEvidenceAppraiser,
    RuleBasedEvidenceSynthesizer,
)
from app.adapters.evidence_planner import RuleBasedEvidencePlanner
from app.adapters.problem_framer import RuleBasedProblemFramer
from app.adapters.sqlite_evidence_store import SQLiteEvidenceStore
from app.adapters.sqlite_project_store import SQLiteProjectStore
from app.domain.evidence import (
    EvidenceDocument,
    AppraisalConfidence,
    EvidenceAppraisalContent,
    EvidenceAppraisalReviewRequest,
    EvidenceItemContent,
    EvidenceItemReviewRequest,
    EvidenceItemStatus,
    EvidenceSynthesisContent,
    EvidenceSynthesisReviewRequest,
    EvidenceStage,
    LiteratureCandidate,
    ParsedDocument,
    ParsedPage,
    ScreeningRequest,
    ScreeningStatus,
    SourceExcerpt,
    SynthesisClaim,
    ReviewStatus,
)
from app.domain.evidence_ports import DocumentValidationError
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


class FakeDocumentStorage:
    def __init__(self) -> None:
        self.saved: dict[str, bytes] = {}

    def save(
        self,
        project_id: UUID,
        candidate_id: UUID,
        filename: str,
        content_type: str,
        content: bytes,
        page_count: int,
    ) -> EvidenceDocument:
        document_id = uuid4()
        storage_key = f"{project_id}/{candidate_id}/{document_id}.pdf"
        self.saved[storage_key] = content
        return EvidenceDocument(
            id=document_id,
            candidate_id=candidate_id,
            filename=filename,
            content_type=content_type,
            byte_size=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
            storage_key=storage_key,
            page_count=page_count,
        )

    def delete(self, storage_key: str) -> None:
        self.saved.pop(storage_key, None)

    def read(self, storage_key: str) -> bytes:
        return self.saved[storage_key]


class FakePdfTextExtractor:
    def parse(self, _content: bytes) -> ParsedDocument:
        return ParsedDocument(
            pages=[
                ParsedPage(
                    page_number=1,
                    text=(
                        "This controlled study recruited N = 24 operators. "
                        "Cognitive workload and task errors were measured."
                    ),
                )
            ]
        )


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
        FakeDocumentStorage(),
        FakePdfTextExtractor(),
        RuleBasedEvidenceExtractor(),
        RuleBasedEvidenceAppraiser(),
        RuleBasedEvidenceSynthesizer(),
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

    review = workflow.upload_pdf(
        project.id,
        candidate.id,
        "study.pdf",
        "application/pdf",
        b"%PDF-1.7 test fixture",
    )
    assert review.documents[0].page_count == 1
    assert review.evidence_items[0].sample_size == 24
    assert review.evidence_items[0].status is EvidenceItemStatus.PENDING_REVIEW

    with pytest.raises(ValueError, match="cannot be excluded"):
        workflow.screen_candidate(
            project.id,
            candidate.id,
            ScreeningRequest(
                status=ScreeningStatus.EXCLUDED,
                reason="全文核验后发现研究对象不符",
            ),
        )

    draft = review.evidence_items[0]
    content = EvidenceItemContent.model_validate(
        draft.model_dump(include=set(EvidenceItemContent.model_fields))
    )
    invalid_content = content.model_copy(
        update={
            "source_excerpts": [
                SourceExcerpt(
                    page_number=1,
                    text="This sentence does not exist in the source PDF.",
                    relevance="无效测试片段",
                )
            ]
        }
    )
    with pytest.raises(DocumentValidationError, match="could not be verified"):
        workflow.review_evidence_item(
            project.id,
            draft.id,
            EvidenceItemReviewRequest(
                content=invalid_content,
                status=EvidenceItemStatus.APPROVED,
            ),
        )

    review = workflow.review_evidence_item(
        project.id,
        draft.id,
        EvidenceItemReviewRequest(
            content=content,
            status=EvidenceItemStatus.APPROVED,
            note="已对照原文核验样本量和研究方法",
        ),
    )
    assert review.evidence_items[0].status is EvidenceItemStatus.APPROVED
    assert review.evidence_items[0].generation.generator == "human"

    review = workflow.appraise_evidence_item(project.id, draft.id)
    appraisal = review.appraisals[0]
    assert appraisal.status is ReviewStatus.PENDING_REVIEW
    appraisal_content = EvidenceAppraisalContent.model_validate(
        appraisal.model_dump(include=set(EvidenceAppraisalContent.model_fields))
    )
    review = workflow.review_appraisal(
        project.id,
        appraisal.id,
        EvidenceAppraisalReviewRequest(
            content=appraisal_content,
            status=ReviewStatus.APPROVED,
            note="已核验研究设计与偏倚风险",
        ),
    )
    assert review.appraisals[0].status is ReviewStatus.APPROVED

    review = workflow.generate_synthesis(project.id)
    assert review.synthesis is not None
    assert len(review.synthesis.matrix) == 1
    synthesis_content = EvidenceSynthesisContent.model_validate(
        review.synthesis.model_dump(include=set(EvidenceSynthesisContent.model_fields))
    )
    invalid_synthesis = synthesis_content.model_copy(
        update={
            "consistent_findings": [
                SynthesisClaim(
                    statement="单篇研究被错误标记为跨研究一致结论",
                    evidence_item_ids=[draft.id],
                    confidence=AppraisalConfidence.LOW,
                    rationale="用于验证跨研究引用约束",
                )
            ]
        }
    )
    with pytest.raises(ValueError, match="at least two evidence items"):
        workflow.review_synthesis(
            project.id,
            EvidenceSynthesisReviewRequest(
                content=invalid_synthesis,
                status=ReviewStatus.APPROVED,
            ),
        )
    review = workflow.review_synthesis(
        project.id,
        EvidenceSynthesisReviewRequest(
            content=synthesis_content,
            status=ReviewStatus.APPROVED,
            note="已核对矩阵、证据缺口与适用范围",
        ),
    )
    assert review.synthesis is not None
    assert review.synthesis.status is ReviewStatus.APPROVED
