import json

from app.adapters.openai_responses import (
    OpenAIResponsesGenerator,
    StructuredGenerationError,
)
from app.domain.ports import ProblemFramingError
from app.domain.project import (
    ClarificationQuestion,
    ClarificationQuestionSet,
    GenerationMetadata,
    ProblemFrame,
    ProblemFrameContent,
    ProjectIntake,
)

class OpenAIProblemFramer:
    prompt_version = "problem-framing-v1"

    def __init__(self, generator: OpenAIResponsesGenerator) -> None:
        self._generator = generator

    def identify_gaps(self, intake: ProjectIntake) -> list[ClarificationQuestion]:
        try:
            result = self._generator.generate(
                ClarificationQuestionSet,
                "clarification_questions",
                self._system_prompt(),
                (
                    "请识别将以下痛点转化为可检验人因研究问题时最关键的信息缺口。"
                    "只提出3到5个高价值问题，不要假设因果关系。\n\n"
                    f"项目输入：{intake.model_dump_json(indent=2)}"
                ),
            )
        except StructuredGenerationError as error:
            raise ProblemFramingError(str(error)) from error
        return result.questions

    def frame(
        self,
        intake: ProjectIntake,
        clarification_answers: dict[str, str],
        revision_feedback: str | None = None,
    ) -> ProblemFrame:
        try:
            content = self._generator.generate(
                ProblemFrameContent,
                "problem_frame",
                self._system_prompt(),
                (
                    "请生成结构化问题界定。必须区分观察、假设和未知信息，"
                    "不能把相关关系表述为因果关系。\n\n"
                    f"项目输入：{intake.model_dump_json(indent=2)}\n\n"
                    f"澄清回答：{json.dumps(clarification_answers, ensure_ascii=False, indent=2)}\n\n"
                    f"上一版修改意见：{revision_feedback or '无'}"
                ),
            )
        except StructuredGenerationError as error:
            raise ProblemFramingError(str(error)) from error
        return ProblemFrame(
            **content.model_dump(),
            generation=GenerationMetadata(
                generator="openai",
                model=self._generator.model,
                prompt_version=self.prompt_version,
            ),
        )

    @staticmethod
    def _system_prompt() -> str:
        return (
            "你是一名严谨的人因工程研究助手。你负责把现场痛点转化为可检验问题，"
            "识别物理、认知和组织人因构念，并明确不确定性。不得虚构数据、文献、"
            "量表效度或因果关系。所有输出必须使用简体中文。"
        )

