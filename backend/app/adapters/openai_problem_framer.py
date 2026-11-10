import json
from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.domain.ports import ProblemFramingError
from app.domain.project import (
    ClarificationQuestion,
    ClarificationQuestionSet,
    GenerationMetadata,
    ProblemFrame,
    ProblemFrameContent,
    ProjectIntake,
)

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class OpenAIResponsesGenerator:
    """Generate schema-validated artifacts through the OpenAI Responses interface."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def generate(
        self,
        output_type: type[OutputModel],
        schema_name: str,
        system_prompt: str,
        user_prompt: str,
    ) -> OutputModel:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                },
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": user_prompt}],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": self._openai_schema(output_type),
                }
            },
        }
        try:
            response = self._client.post("/responses", json=payload)
            response.raise_for_status()
            response_data = response.json()
            output_text = self._extract_output_text(response_data)
            return output_type.model_validate_json(output_text)
        except ProblemFramingError:
            raise
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise ProblemFramingError(f"Model generation failed: {error}") from error

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @staticmethod
    def _openai_schema(output_type: type[BaseModel]) -> dict:
        """Remove JSON Schema annotations unsupported by strict Structured Outputs."""

        def clean(value):
            if isinstance(value, dict):
                return {
                    key: clean(item)
                    for key, item in value.items()
                    if key not in {"default", "minLength", "maxLength", "title"}
                }
            if isinstance(value, list):
                return [clean(item) for item in value]
            return value

        return clean(output_type.model_json_schema())

    @staticmethod
    def _extract_output_text(response_data: dict) -> str:
        if isinstance(response_data.get("output_text"), str):
            return response_data["output_text"]
        for item in response_data.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "refusal":
                    raise ProblemFramingError(content.get("refusal", "Model refused"))
                if content.get("type") == "output_text":
                    return content["text"]
        raise ProblemFramingError("Model response did not contain structured output")


class OpenAIProblemFramer:
    prompt_version = "problem-framing-v1"

    def __init__(self, generator: OpenAIResponsesGenerator) -> None:
        self._generator = generator

    def identify_gaps(self, intake: ProjectIntake) -> list[ClarificationQuestion]:
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
        return result.questions

    def frame(
        self,
        intake: ProjectIntake,
        clarification_answers: dict[str, str],
        revision_feedback: str | None = None,
    ) -> ProblemFrame:
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

