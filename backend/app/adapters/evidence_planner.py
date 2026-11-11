import json
from datetime import datetime, timezone

from app.adapters.openai_responses import (
    OpenAIResponsesGenerator,
    StructuredGenerationError,
)
from app.domain.evidence import SearchPlan, SearchPlanContent
from app.domain.evidence_ports import EvidencePlanningError
from app.domain.project import GenerationMetadata, Project


class RuleBasedEvidencePlanner:
    prompt_version = "evidence-plan-rule-v1"

    _translations = {
        "疲劳": "fatigue",
        "疲劳与昼夜节律": "fatigue circadian rhythm",
        "认知负荷": "cognitive workload",
        "心理负荷": "mental workload",
        "人的可靠性": "human reliability error",
        "可用性": "usability human computer interaction",
        "作业绩效": "task performance",
        "工作姿势与肌肉骨骼负荷": "working posture musculoskeletal workload",
        "肌肉骨骼不适": "musculoskeletal discomfort",
        "错误率": "error rate",
        "任务完成时间与产出率": "task completion time productivity",
        "主观疲劳评分": "subjective fatigue rating",
        "主观心理负荷评分": "subjective workload rating",
        "可用性量表得分": "usability scale score",
    }

    def plan(self, project: Project) -> SearchPlan:
        if project.problem_frame is None:
            raise EvidencePlanningError("An approved problem frame is required")
        terms = [
            self._translations.get(item, item)
            for item in [
                *project.problem_frame.human_factors_constructs,
                *project.problem_frame.candidate_outcomes,
            ]
        ]
        keywords = list(dict.fromkeys(["human factors", *terms]))[:12]
        current_year = datetime.now(timezone.utc).year
        return SearchPlan(
            query=" ".join(keywords),
            keywords=keywords,
            inclusion_criteria=[
                f"研究对象或情境与“{project.intake.population}”具有可比性",
                "报告可识别的人因变量与任务、绩效或体验结果",
                "具有可核验的 DOI 或来源页面",
            ],
            exclusion_criteria=[
                "仅为观点文章且没有研究方法或数据",
                "研究问题与当前人因构念无明显关系",
                "书目信息不足，无法核验来源",
            ],
            from_year=max(1990, current_year - 15),
            until_year=current_year,
            max_results=20,
            generation=GenerationMetadata(
                generator="rule_based",
                model=None,
                prompt_version=self.prompt_version,
            ),
        )

class OpenAIEvidencePlanner:
    prompt_version = "evidence-plan-v1"

    def __init__(self, generator: OpenAIResponsesGenerator) -> None:
        self._generator = generator

    def plan(self, project: Project) -> SearchPlan:
        if project.problem_frame is None:
            raise EvidencePlanningError("An approved problem frame is required")
        try:
            content = self._generator.generate(
                SearchPlanContent,
                "literature_search_plan",
                (
                    "你是一名人因工程文献检索助手。生成可复现的英文书目检索策略。"
                    "关键词应包含构念、目标人群或任务以及结果指标。纳入和排除标准必须"
                    "可由标题与书目信息初筛，不得虚构数据库专用语法。"
                ),
                json.dumps(
                    {
                        "intake": project.intake.model_dump(mode="json"),
                        "problem_frame": project.problem_frame.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
        except StructuredGenerationError as error:
            raise EvidencePlanningError(str(error)) from error
        return SearchPlan(
            **content.model_dump(),
            generation=GenerationMetadata(
                generator="openai",
                model=self._generator.model,
                prompt_version=self.prompt_version,
            ),
        )
