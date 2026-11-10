from app.domain.project import (
    ClarificationQuestion,
    GenerationMetadata,
    ProblemFrame,
    ProjectIntake,
)


class RuleBasedProblemFramer:
    """Deterministic adapter used when no model credentials are configured."""

    prompt_version = "rule-v2"

    _construct_keywords = {
        "疲劳": "疲劳",
        "夜班": "疲劳与昼夜节律",
        "认知": "认知负荷",
        "负荷": "心理负荷",
        "错误": "人的可靠性",
        "失误": "人的可靠性",
        "可用性": "可用性",
        "界面": "可用性",
        "效率": "作业绩效",
        "姿势": "工作姿势与肌肉骨骼负荷",
        "疼痛": "肌肉骨骼不适",
    }

    _outcome_keywords = {
        "错误": "错误率",
        "失误": "操作失误率",
        "效率": "任务完成时间与产出率",
        "疲劳": "主观疲劳评分",
        "负荷": "主观心理负荷评分",
        "可用性": "可用性量表得分",
        "疼痛": "不适或疼痛评分",
    }

    def identify_gaps(self, intake: ProjectIntake) -> list[ClarificationQuestion]:
        return [
            ClarificationQuestion(
                id="baseline_severity",
                prompt="这个问题目前的发生频率、严重程度或基线数据是什么？",
                rationale="需要基线才能判断问题规模并选择结果指标。",
            ),
            ClarificationQuestion(
                id="suspected_factors",
                prompt="你目前怀疑哪些人员、任务、设备或环境因素与该问题有关？",
                rationale="候选因素用于形成可检验假设，并识别潜在混杂因素。",
            ),
            ClarificationQuestion(
                id="decision_goal",
                prompt="研究结果最终需要支持什么决策或改进动作？",
                rationale="决策目标决定实验精度、比较条件和建议形式。",
            ),
        ]

    def frame(
        self,
        intake: ProjectIntake,
        clarification_answers: dict[str, str],
        revision_feedback: str | None = None,
    ) -> ProblemFrame:
        source = " ".join(
            [intake.pain_point, intake.context, *clarification_answers.values()]
        )
        constructs = self._matched_values(source, self._construct_keywords)
        outcomes = self._matched_values(source, self._outcome_keywords)
        if not constructs:
            constructs = ["待确认的人因构念"]
        if not outcomes:
            outcomes = ["任务绩效", "主观体验"]

        assumptions = [
            "当前痛点来自真实工作或使用情境中的持续观察",
            "可以获取至少一种客观或主观结果指标",
        ]
        baseline = clarification_answers.get("baseline_severity")
        if baseline:
            assumptions.append(f"用户提供的当前基线：{baseline}")
        if revision_feedback:
            assumptions.append(f"本版已考虑修改意见：{revision_feedback}")

        return ProblemFrame(
            research_question=(
                f"在{intake.context}中，哪些人因因素与{intake.population}的"
                f"“{intake.pain_point}”有关，以及可通过哪些可测量指标验证？"
            ),
            human_factors_constructs=constructs,
            candidate_outcomes=outcomes,
            assumptions=assumptions,
            uncertainties=[
                "潜在混杂因素与可控变量仍需在实验设计阶段确认",
                "测量工具的信效度和适用人群尚未核验",
                "因果关系不能仅由当前痛点描述推断",
            ],
            generation=GenerationMetadata(
                generator="rule_based",
                model=None,
                prompt_version=self.prompt_version,
            ),
        )

    @staticmethod
    def _matched_values(source: str, mapping: dict[str, str]) -> list[str]:
        return list(dict.fromkeys(value for key, value in mapping.items() if key in source))

