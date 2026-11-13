import json

from app.adapters.openai_responses import (
    OpenAIResponsesGenerator,
    StructuredGenerationError,
)
from app.domain.evidence import EvidenceSynthesis
from app.domain.experiment import (
    EvidenceGroundedDecision,
    ExperimentalCondition,
    ExperimentDesignType,
    ExperimentHypothesis,
    ExperimentPlan,
    ExperimentPlanContent,
    HypothesisDirection,
    ParticipantPlan,
    ProcedureStep,
    SampleSizePlanning,
    StatisticalAnalysisPlan,
    VariableRole,
    VariableSpecification,
)
from app.domain.experiment_ports import ExperimentDesignError
from app.domain.project import GenerationMetadata, Project


class RuleBasedExperimentDesigner:
    """Create a conservative, editable protocol without fabricating power results."""

    prompt_version = "rule-experiment-v1"

    def design(
        self,
        project: Project,
        synthesis: EvidenceSynthesis,
        synthesis_hash: str,
    ) -> ExperimentPlan:
        if project.problem_frame is None:
            raise ExperimentDesignError("Approved problem frame is missing")
        rows = synthesis.matrix
        evidence_ids = [row.evidence_item_id for row in rows]
        independent = self._first_unique(
            item for row in rows for item in row.exposures_or_interventions
        )
        dependent = self._first_unique(
            item for row in rows for item in row.outcomes_and_measures
        )
        independent = independent or project.problem_frame.human_factors_constructs[:1]
        dependent = dependent or project.problem_frame.candidate_outcomes[:1]
        if not independent or not dependent:
            raise ExperimentDesignError(
                "Evidence synthesis must identify at least one candidate factor and outcome"
            )
        primary_iv = independent[0]
        primary_dv = dependent[0]
        variables = [
            VariableSpecification(
                name=name,
                role=VariableRole.INDEPENDENT,
                operational_definition="待人工定义可复现的实验水平、操纵范围和实施方式",
                measurement_method="实验条件记录或系统日志，具体方法待确认",
                measurement_timing="每个实验条件开始前与执行期间",
                evidence_item_ids=evidence_ids,
            )
            for name in independent[:3]
        ]
        variables.extend(
            VariableSpecification(
                name=name,
                role=VariableRole.DEPENDENT,
                operational_definition="待人工定义指标算法、单位、有效范围和异常值规则",
                measurement_method=self._measurement_for(name, rows),
                measurement_timing="基线及每个实验条件结束后，具体时点待确认",
                evidence_item_ids=evidence_ids,
            )
            for name in dependent[:3]
        )
        hypothesis = ExperimentHypothesis(
            statement=(
                f"在{project.intake.context}中，{primary_iv}的不同水平与"
                f"{primary_dv}存在可检验差异。"
            ),
            null_hypothesis=f"{primary_iv}的不同水平在{primary_dv}上不存在差异。",
            direction=HypothesisDirection.NON_DIRECTIONAL,
            primary_outcome=primary_dv,
            evidence_item_ids=evidence_ids,
        )
        content = ExperimentPlanContent(
            title=f"{project.intake.name}实验方案草案",
            objective=project.problem_frame.research_question,
            design_type=ExperimentDesignType.UNDECIDED,
            hypotheses=[hypothesis],
            conditions=[
                ExperimentalCondition(
                    name="基线或对照条件",
                    description="保持当前流程或参考状态；需人工补充可复现定义",
                ),
                ExperimentalCondition(
                    name="实验或比较条件",
                    description=f"操纵{primary_iv}；具体水平、材料和实施方式待人工确认",
                ),
            ],
            variables=variables,
            participant_plan=ParticipantPlan(
                target_population=project.intake.population,
                inclusion_criteria=[f"属于目标人群：{project.intake.population}"],
                exclusion_criteria=["无法完成知情同意或核心实验任务"],
                recruitment_strategy="待结合现场可达性、班次和伦理要求制定招募方案",
                sampling_method="待确认概率抽样、分层抽样或便利抽样及其局限",
            ),
            sample_size_planning=SampleSizePlanning(
                planned_primary_test="待根据最终设计和主要结局选择确定性统计检验",
                effect_size_metric=None,
                expected_effect_size=None,
                effect_size_basis="待从已批准证据、预实验或最小实际重要差异中确定",
                alpha=None,
                target_power=None,
                attrition_allowance=None,
                calculation_note=(
                    "尚未进行功效分析；不得把模型生成的数字当作所需样本量。"
                    "最终样本量必须由后续确定性计算模块给出。"
                ),
            ),
            randomization_plan="设计类型尚未确定；需人工定义随机分配或随机呈现方法",
            counterbalancing_plan="若采用组内或混合设计，需确定顺序平衡和学习效应控制方案",
            procedure=[
                ProcedureStep(
                    order=1,
                    name="知情同意与资格确认",
                    description="说明研究风险、退出权利并核验纳排标准",
                    duration_minutes=None,
                    data_collected=["知情同意状态", "资格筛选结果"],
                ),
                ProcedureStep(
                    order=2,
                    name="基线测量与训练",
                    description="记录必要基线并确保参与者理解任务，但避免过度训练",
                    duration_minutes=None,
                    data_collected=["基线指标", "训练完成状态"],
                ),
                ProcedureStep(
                    order=3,
                    name="实验任务",
                    description="按最终随机化或顺序平衡方案执行各实验条件",
                    duration_minutes=None,
                    data_collected=[primary_dv, "操纵与过程日志"],
                ),
                ProcedureStep(
                    order=4,
                    name="结束测量与说明",
                    description="完成主观测量、不良事件询问和实验后说明",
                    duration_minutes=None,
                    data_collected=["结束测量", "不良事件", "退出原因"],
                ),
            ],
            analysis_plan=[
                StatisticalAnalysisPlan(
                    hypothesis_index=1,
                    method="待根据设计类型、变量尺度和分布选择统计方法",
                    outcome=primary_dv,
                    predictors=[primary_iv],
                    assumptions_to_check=["独立性", "分布与残差", "方差结构"],
                    missing_data_strategy="预先定义缺失原因、分析集和敏感性分析",
                    multiplicity_strategy="若存在多个结局或比较，预先定义主要结局和校正方法",
                )
            ],
            ethics_and_safety=[
                "获得知情同意并允许参与者随时无惩罚退出",
                "最小化疲劳、压力、隐私泄露和工作绩效风险",
                "明确不良事件、暂停实验和数据保密流程",
            ],
            assumptions=[
                "当前批准的证据综合足以支持提出可检验的非方向性假设",
                "目标现场允许在不影响安全和生产的前提下实施实验任务",
            ],
            uncertainties=[
                "实验设计类型、条件水平和操纵强度尚未确认",
                "主要结局、测量时点和最小实际重要差异尚未锁定",
                "样本量尚未进行确定性功效分析",
            ],
            evidence_grounded_decisions=[
                EvidenceGroundedDecision(
                    decision=f"优先检验{primary_iv}与{primary_dv}之间的关系",
                    rationale="该因素与结果指标出现在已批准的跨文献证据矩阵中",
                    evidence_item_ids=evidence_ids,
                )
            ],
        )
        return ExperimentPlan(
            **content.model_dump(),
            project_id=project.id,
            source_synthesis_id=synthesis.id,
            source_synthesis_hash=synthesis_hash,
            generation=GenerationMetadata(
                generator="rule-based",
                model=None,
                prompt_version=self.prompt_version,
            ),
        )

    @staticmethod
    def _first_unique(values, limit: int = 6) -> list[str]:
        result: list[str] = []
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in result:
                result.append(normalized)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _measurement_for(name: str, rows) -> str:
        for row in rows:
            matches = [item for item in row.outcomes_and_measures if item == name]
            if matches:
                return f"依据证据矩阵中的 {name}，具体量表、设备或算法待人工核验"
        return "测量工具或算法待人工确认"


class OpenAIExperimentDesigner:
    prompt_version = "experiment-design-v1"

    def __init__(self, generator: OpenAIResponsesGenerator) -> None:
        self._generator = generator

    def design(
        self,
        project: Project,
        synthesis: EvidenceSynthesis,
        synthesis_hash: str,
    ) -> ExperimentPlan:
        try:
            content = self._generator.generate(
                ExperimentPlanContent,
                schema_name="human_factors_experiment_plan",
                system_prompt=(
                    "你是严谨的人因工程实验设计助手。只能使用已批准的项目问题和证据综合。"
                    "每个假设、变量和关键决策必须引用真实 evidence_item_ids。证据不足时把"
                    "design_type 设为 undecided 并写入 uncertainties。不得生成最终样本量；"
                    "sample_size_planning 只能记录功效分析输入，未知值使用 null。统计方法必须"
                    "与设计和变量类型匹配，仍不确定时明确写待确认。"
                ),
                user_prompt=json.dumps(
                    {
                        "project": project.model_dump(mode="json"),
                        "approved_synthesis": synthesis.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                ),
            )
        except StructuredGenerationError as error:
            raise ExperimentDesignError(str(error)) from error
        return ExperimentPlan(
            **content.model_dump(),
            project_id=project.id,
            source_synthesis_id=synthesis.id,
            source_synthesis_hash=synthesis_hash,
            generation=GenerationMetadata(
                generator="openai",
                model=self._generator.model,
                prompt_version=self.prompt_version,
            ),
        )
