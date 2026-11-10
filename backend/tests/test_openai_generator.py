import json

import httpx

from app.adapters.openai_problem_framer import OpenAIResponsesGenerator
from app.domain.project import ProblemFrameContent


def test_openai_generator_sends_strict_schema_and_parses_output() -> None:
    content = {
        "research_question": "不同界面信息密度是否与操作员任务错误率和认知负荷相关？",
        "human_factors_constructs": ["认知负荷", "可用性"],
        "candidate_outcomes": ["错误率", "NASA-TLX 得分"],
        "assumptions": ["参与者执行相同任务"],
        "uncertainties": ["操作经验可能构成混杂因素"],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        schema = payload["text"]["format"]
        assert request.url.path == "/v1/responses"
        assert schema["type"] == "json_schema"
        assert schema["strict"] is True
        assert schema["schema"]["additionalProperties"] is False
        assert "minLength" not in json.dumps(schema["schema"])
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "content": [
                            {"type": "output_text", "text": json.dumps(content)}
                        ]
                    }
                ]
            },
        )

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://api.openai.com/v1",
    )
    generator = OpenAIResponsesGenerator(
        api_key="test-key",
        model="test-model",
        client=client,
    )

    result = generator.generate(
        ProblemFrameContent,
        "problem_frame",
        "system",
        "user",
    )

    assert result.research_question == content["research_question"]
    assert result.human_factors_constructs == ["认知负荷", "可用性"]

