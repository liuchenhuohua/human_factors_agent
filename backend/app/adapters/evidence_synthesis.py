import json

from pydantic import BaseModel, ConfigDict

from app.adapters.openai_responses import (
    OpenAIResponsesGenerator,
    StructuredGenerationError,
)
from app.domain.evidence import (
    AppraisalConcern,
    AppraisalConfidence,
    AppraisalJudgment,
    EvidenceAppraisal,
    EvidenceAppraisalContent,
    EvidenceItem,
    EvidenceMatrixRow,
    EvidenceReview,
    EvidenceSynthesis,
    LiteratureCandidate,
    SynthesisClaim,
)
from app.domain.evidence_ports import EvidenceAppraisalError, EvidenceSynthesisError
from app.domain.project import GenerationMetadata, Project


class RuleBasedEvidenceAppraiser:
    """Produce a conservative appraisal draft without inventing methodological facts."""

    prompt_version = "rule-appraisal-v1"

    def appraise(
        self,
        project: Project,
        candidate: LiteratureCandidate,
        item: EvidenceItem,
    ) -> EvidenceAppraisal:
        del project, candidate
        content = EvidenceAppraisalContent(
            design_appropriateness=self._reported_or_unclear(
                item.study_design,
                "研究设计已被提取，但仍需人工判断其是否适合研究问题",
                "全文提取结果未提供足够的研究设计信息",
            ),
            sample_adequacy=self._reported_or_unclear(
                item.sample_size,
                "样本量已报告，但仍需结合功效分析、组数和任务变异判断充分性",
                "未提取到样本量或样本充分性依据",
            ),
            measurement_validity=self._reported_or_unclear(
                item.measures,
                "测量工具已报告，但信效度及对目标构念的覆盖仍需人工核验",
                "未提取到足够的测量工具信息",
            ),
            analysis_adequacy=self._reported_or_unclear(
                item.statistical_methods,
                "统计方法已报告，但假设检验条件、多重比较和模型设定仍需核验",
                "未提取到足够的统计分析信息",
            ),
            bias_risk=AppraisalJudgment(
                concern=AppraisalConcern.UNCLEAR,
                rationale="规则模式无法可靠判断分配、盲法、缺失数据、选择性报告或混杂偏倚",
            ),
            directness=self._reported_or_unclear(
                item.participants or item.task_context,
                "人群或任务场景已报告，但与当前项目的可迁移性仍需人工判断",
                "缺少足够的人群或任务场景信息，无法判断直接性",
            ),
            overall_confidence=AppraisalConfidence.UNCLEAR,
            strengths=self._strengths(item),
            concerns=self._concerns(item),
        )
        return EvidenceAppraisal(
            **content.model_dump(),
            evidence_item_id=item.id,
            generation=GenerationMetadata(
                generator="rule-based",
                model=None,
                prompt_version=self.prompt_version,
            ),
        )

    @staticmethod
    def _reported_or_unclear(value, present: str, missing: str) -> AppraisalJudgment:
        if value:
            return AppraisalJudgment(
                concern=AppraisalConcern.SOME_CONCERNS,
                rationale=present,
            )
        return AppraisalJudgment(
            concern=AppraisalConcern.UNCLEAR,
            rationale=missing,
        )

    @staticmethod
    def _strengths(item: EvidenceItem) -> list[str]:
        strengths: list[str] = []
        if item.source_excerpts:
            strengths.append("关键提取字段保留了可回溯的页码原文")
        if item.effect_sizes:
            strengths.append("报告了效应量信息")
        if item.control_variables:
            strengths.append("报告了控制变量或混杂因素")
        return strengths

    @staticmethod
    def _concerns(item: EvidenceItem) -> list[str]:
        concerns: list[str] = []
        if item.sample_size is None:
            concerns.append("样本量信息缺失")
        if not item.effect_sizes:
            concerns.append("未提取到效应量或不确定性区间")
        if not item.limitations:
            concerns.append("未提取到作者报告的局限")
        return concerns


class OpenAIEvidenceAppraiser:
    prompt_version = "evidence-appraisal-v1"

    def __init__(self, generator: OpenAIResponsesGenerator) -> None:
        self._generator = generator

    def appraise(
        self,
        project: Project,
        candidate: LiteratureCandidate,
        item: EvidenceItem,
    ) -> EvidenceAppraisal:
        try:
            content = self._generator.generate(
                EvidenceAppraisalContent,
                schema_name="human_factors_evidence_appraisal",
                system_prompt=(
                    "你是人因工程研究质量评价助手。根据提供的结构化证据生成透明、保守的"
                    "评价草案。这不是正式的 GRADE、RoB 2 或 ROBINS-I 评价。信息不足时必须"
                    "使用 unclear，不得假设随机化、盲法、功效或量表效度。directness 只评价"
                    "研究人群、任务、暴露和结局对当前项目的适用性。"
                ),
                user_prompt=json.dumps(
                    {
                        "project": project.model_dump(mode="json"),
                        "candidate": candidate.model_dump(mode="json"),
                        "evidence_item": item.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                ),
            )
        except StructuredGenerationError as error:
            raise EvidenceAppraisalError(str(error)) from error
        return EvidenceAppraisal(
            **content.model_dump(),
            evidence_item_id=item.id,
            generation=GenerationMetadata(
                generator="openai",
                model=self._generator.model,
                prompt_version=self.prompt_version,
            ),
        )


class SynthesisNarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consistent_findings: list[SynthesisClaim]
    conflicting_findings: list[SynthesisClaim]
    evidence_gaps: list[str]
    transferability_notes: list[str]
    cautions: list[str]


class RuleBasedEvidenceSynthesizer:
    prompt_version = "rule-synthesis-v1"

    def synthesize(self, project: Project, review: EvidenceReview) -> EvidenceSynthesis:
        pairs = review.approved_evidence_with_appraisals()
        matrix = build_matrix(review, pairs)
        gaps = ["规则模式不会自动声称跨研究结果一致或冲突，需要人工逐项综合"]
        if len(pairs) == 1:
            gaps.append("当前只有一项已评价证据，无法判断跨研究一致性")
        if any(not item.effect_sizes for item, _ in pairs):
            gaps.append("至少一项研究缺少效应量或不确定性区间，不能进行定量合并")
        return EvidenceSynthesis(
            matrix=matrix,
            consistent_findings=[],
            conflicting_findings=[],
            evidence_gaps=gaps,
            transferability_notes=[
                f"目标人群：{project.intake.population}",
                f"目标场景：{project.intake.context}",
                "需人工比较每项研究的人群、任务和结果指标与当前项目的差异",
            ],
            cautions=[
                "不同研究设计、量表或结局定义不得直接合并效应量",
                "该综合草案只有经过人工批准后才能进入实验设计",
            ],
            generation=GenerationMetadata(
                generator="rule-based",
                model=None,
                prompt_version=self.prompt_version,
            ),
        )


class OpenAIEvidenceSynthesizer:
    prompt_version = "evidence-synthesis-v1"

    def __init__(self, generator: OpenAIResponsesGenerator) -> None:
        self._generator = generator

    def synthesize(self, project: Project, review: EvidenceReview) -> EvidenceSynthesis:
        pairs = review.approved_evidence_with_appraisals()
        matrix = build_matrix(review, pairs)
        allowed_ids = {item.id for item, _ in pairs}
        try:
            narrative = self._generator.generate(
                SynthesisNarrative,
                schema_name="human_factors_evidence_synthesis",
                system_prompt=(
                    "你是人因工程证据综合助手。只使用已批准的证据和评价。保留冲突和"
                    "不确定性，不得把不同人群、设计、量表或结局的效应量直接合并。每条"
                    "一致或冲突结论必须引用支持它的 evidence_item_ids；单篇研究不能形成"
                    "跨研究一致性结论。输出是待人工审核的叙述性综合，不是元分析。"
                ),
                user_prompt=json.dumps(
                    {
                        "project": project.model_dump(mode="json"),
                        "evidence": [
                            {
                                "item": item.model_dump(mode="json"),
                                "appraisal": appraisal.model_dump(mode="json"),
                            }
                            for item, appraisal in pairs
                        ],
                    },
                    ensure_ascii=False,
                ),
            )
        except StructuredGenerationError as error:
            raise EvidenceSynthesisError(str(error)) from error
        for claim in [
            *narrative.consistent_findings,
            *narrative.conflicting_findings,
        ]:
            if not set(claim.evidence_item_ids).issubset(allowed_ids):
                raise EvidenceSynthesisError(
                    "Synthesis referenced an unapproved evidence item"
                )
            if len(set(claim.evidence_item_ids)) < 2:
                raise EvidenceSynthesisError(
                    "A cross-study claim requires at least two evidence items"
                )
        return EvidenceSynthesis(
            matrix=matrix,
            **narrative.model_dump(),
            generation=GenerationMetadata(
                generator="openai",
                model=self._generator.model,
                prompt_version=self.prompt_version,
            ),
        )


def build_matrix(
    review: EvidenceReview,
    pairs: list[tuple[EvidenceItem, EvidenceAppraisal]],
) -> list[EvidenceMatrixRow]:
    candidates = {candidate.id: candidate for candidate in review.candidates}
    rows: list[EvidenceMatrixRow] = []
    for item, appraisal in pairs:
        candidate = candidates[item.candidate_id]
        citation = candidate.title
        if candidate.publication_year:
            citation = f"{citation} ({candidate.publication_year})"
        rows.append(
            EvidenceMatrixRow(
                evidence_item_id=item.id,
                candidate_id=candidate.id,
                citation=citation,
                population_and_context="；".join(
                    part for part in [item.participants, item.task_context] if part
                )
                or "未充分报告",
                design_and_sample="；".join(
                    part
                    for part in [
                        item.study_design,
                        f"样本量 n={item.sample_size}" if item.sample_size else None,
                    ]
                    if part
                )
                or "未充分报告",
                exposures_or_interventions=item.independent_variables,
                outcomes_and_measures=[*item.dependent_variables, *item.measures],
                findings_and_effects=[*item.key_findings, *item.effect_sizes],
                limitations=item.limitations,
                appraisal_confidence=appraisal.overall_confidence,
            )
        )
    return rows
