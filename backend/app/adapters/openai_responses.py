from typing import TypeVar

import httpx
from pydantic import BaseModel

OutputModel = TypeVar("OutputModel", bound=BaseModel)


class StructuredGenerationError(RuntimeError):
    """Raised when a model cannot return a schema-valid artifact."""


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
        except StructuredGenerationError:
            raise
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise StructuredGenerationError(f"Model generation failed: {error}") from error

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @staticmethod
    def _openai_schema(output_type: type[BaseModel]) -> dict:
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
                    raise StructuredGenerationError(content.get("refusal", "Model refused"))
                if content.get("type") == "output_text":
                    return content["text"]
        raise StructuredGenerationError("Model response did not contain structured output")
