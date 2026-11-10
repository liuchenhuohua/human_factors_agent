from app.domain.project import ProblemFrame, ProjectIntake


class RuleBasedProblemFramer:
    """Deterministic first adapter; replaceable by an LLM-backed adapter later."""

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

    def frame(self, intake: ProjectIntake) -> ProblemFrame:
        source = f"{intake.pain_point} {intake.context}"
        constructs = self._matched_values(source, self._construct_keywords)
        outcomes = self._matched_values(source, self._outcome_keywords)

        if not constructs:
            constructs = ["待确认的人因构念"]
        if not outcomes:
            outcomes = ["任务绩效", "主观体验"]

        question = (
            f"在{intake.context}中，哪些人因因素与{intake.population}的"
            f"“{intake.pain_point}”有关，以及可通过哪些可测量指标验证？"
        )

        assumptions = [
            "当前痛点来自真实工作或使用情境中的持续观察",
            "可以获取至少一种客观或主观结果指标",
        ]
        if intake.constraints:
            assumptions.append("研究设计需要遵守已提供的资源与实施约束")

        return ProblemFrame(
            research_question=question,
            human_factors_constructs=constructs,
            candidate_outcomes=outcomes,
            assumptions=assumptions,
            uncertainties=[
                "痛点的发生频率、严重程度和基线尚未量化",
                "潜在混杂因素与可控变量尚未确认",
                "因果关系不能仅由当前痛点描述推断",
            ],
        )

    @staticmethod
    def _matched_values(source: str, mapping: dict[str, str]) -> list[str]:
        return list(dict.fromkeys(value for key, value in mapping.items() if key in source))

