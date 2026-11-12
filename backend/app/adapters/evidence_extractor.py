import json
import re

from app.adapters.openai_responses import (
    OpenAIResponsesGenerator,
    StructuredGenerationError,
)
from app.domain.evidence import (
    EvidenceDocument,
    EvidenceItem,
    EvidenceItemContent,
    LiteratureCandidate,
    ParsedDocument,
    SourceExcerpt,
)
from app.domain.evidence_ports import EvidenceExtractionError
from app.domain.project import GenerationMetadata


class RuleBasedEvidenceExtractor:
    """Create a conservative review draft without claiming facts not found by a model."""

    prompt_version = "rule-evidence-v1"

    def extract(
        self,
        candidate: LiteratureCandidate,
        document: EvidenceDocument,
        parsed: ParsedDocument,
    ) -> EvidenceItem:
        first_page = next(page for page in parsed.pages if page.text)
        excerpt = first_page.text[:1200].strip()
        sample_match = re.search(
            r"\b(?:n\s*=\s*|sample of\s+)(\d{1,6})\b",
            " ".join(page.text for page in parsed.pages),
            flags=re.IGNORECASE,
        )
        return EvidenceItem(
            candidate_id=candidate.id,
            document_id=document.id,
            research_questions=[],
            study_design=None,
            participants=None,
            sample_size=int(sample_match.group(1)) if sample_match else None,
            task_context=None,
            independent_variables=[],
            dependent_variables=[],
            control_variables=[],
            measures=[],
            statistical_methods=[],
            key_findings=[],
            effect_sizes=[],
            limitations=[],
            source_excerpts=[
                SourceExcerpt(
                    page_number=first_page.page_number,
                    text=excerpt,
                    relevance="首个可提取正文片段，供人工核验和补充结构化字段",
                )
            ],
            generation=GenerationMetadata(
                generator="rule-based",
                model=None,
                prompt_version=self.prompt_version,
            ),
        )


class OpenAIEvidenceExtractor:
    prompt_version = "evidence-extraction-v1"

    def __init__(
        self,
        generator: OpenAIResponsesGenerator,
        max_input_characters: int = 100_000,
    ) -> None:
        self._generator = generator
        self._max_input_characters = max_input_characters

    def extract(
        self,
        candidate: LiteratureCandidate,
        document: EvidenceDocument,
        parsed: ParsedDocument,
    ) -> EvidenceItem:
        page_text = self._page_text(parsed)
        try:
            content = self._generator.generate(
                EvidenceItemContent,
                schema_name="human_factors_evidence_item",
                system_prompt=(
                    "你是严谨的人因工程证据提取助手。只提取 PDF 明确陈述的内容，"
                    "缺失信息使用 null 或空列表，禁止根据常识补全。source_excerpts 必须"
                    "逐字来自指定页，并用于支持关键方法或结果。输出语言使用中文，但变量、"
                    "量表和统计方法保留原文术语。"
                ),
                user_prompt=json.dumps(
                    {
                        "candidate": candidate.model_dump(mode="json"),
                        "document": {
                            "filename": document.filename,
                            "page_count": document.page_count,
                        },
                        "pages": page_text,
                    },
                    ensure_ascii=False,
                ),
            )
            self._validate_excerpts(content, parsed)
        except StructuredGenerationError as error:
            raise EvidenceExtractionError(str(error)) from error
        return EvidenceItem(
            **content.model_dump(),
            candidate_id=candidate.id,
            document_id=document.id,
            generation=GenerationMetadata(
                generator="openai",
                model=self._generator.model,
                prompt_version=self.prompt_version,
            ),
        )

    def _page_text(self, parsed: ParsedDocument) -> list[dict[str, int | str]]:
        remaining = self._max_input_characters
        result: list[dict[str, int | str]] = []
        for page in parsed.pages:
            if remaining <= 0:
                break
            text = page.text[:remaining]
            result.append({"page_number": page.page_number, "text": text})
            remaining -= len(text)
        return result

    @staticmethod
    def _validate_excerpts(
        content: EvidenceItemContent,
        parsed: ParsedDocument,
    ) -> None:
        pages = {page.page_number: page.text for page in parsed.pages}
        for excerpt in content.source_excerpts:
            page_text = pages.get(excerpt.page_number)
            if page_text is None:
                raise EvidenceExtractionError(
                    f"Evidence excerpt references missing page {excerpt.page_number}"
                )
            normalized_page = " ".join(page_text.split())
            normalized_excerpt = " ".join(excerpt.text.split())
            if normalized_excerpt not in normalized_page:
                raise EvidenceExtractionError(
                    f"Evidence excerpt could not be verified on page {excerpt.page_number}"
                )
