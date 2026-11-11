from uuid import NAMESPACE_URL, uuid5

import httpx

from app.domain.evidence import LiteratureCandidate, SearchPlanContent
from app.domain.evidence_ports import LiteratureSearchError


class CrossrefLiteratureSearch:
    """Search public Crossref metadata without storing copyrighted abstracts."""

    def __init__(
        self,
        base_url: str = "https://api.crossref.org/v1",
        timeout_seconds: float = 30.0,
        mailto: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._mailto = mailto
        self._owns_client = client is None
        agent = "human-factors-assistant/0.3 (+https://github.com/liuchenhuohua/human_factors_agent)"
        if mailto:
            agent = f"{agent} mailto:{mailto}"
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout_seconds,
            headers={"User-Agent": agent},
        )
    def search(self, plan: SearchPlanContent) -> list[LiteratureCandidate]:
        params: dict[str, str | int] = {
            "query.bibliographic": plan.query,
            "rows": plan.max_results,
            "sort": "relevance",
            "select": "DOI,title,author,published,container-title,URL,type",
        }
        filters: list[str] = []
        if plan.from_year:
            filters.append(f"from-pub-date:{plan.from_year}-01-01")
        if plan.until_year:
            filters.append(f"until-pub-date:{plan.until_year}-12-31")
        if filters:
            params["filter"] = ",".join(filters)
        if self._mailto:
            params["mailto"] = self._mailto

        try:
            response = self._client.get("/works", params=params)
            response.raise_for_status()
            items = response.json()["message"]["items"]
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
            raise LiteratureSearchError(f"Crossref search failed: {error}") from error

        candidates: list[LiteratureCandidate] = []
        seen: set[str] = set()
        for item in items:
            candidate = self._parse_item(item)
            if candidate is None or candidate.source_id in seen:
                continue
            seen.add(candidate.source_id)
            candidates.append(candidate)
        return candidates

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @staticmethod
    def _parse_item(item: dict) -> LiteratureCandidate | None:
        titles = item.get("title") or []
        if not titles or not str(titles[0]).strip():
            return None
        title = str(titles[0]).strip()
        doi = str(item.get("DOI", "")).strip().lower() or None
        source_id = doi or str(item.get("URL", "")).strip() or title
        url = f"https://doi.org/{doi}" if doi else str(item.get("URL", "")).strip()
        if not url:
            return None

        authors = []
        for author in item.get("author") or []:
            name = " ".join(
                part for part in [author.get("given"), author.get("family")] if part
            ).strip()
            if name:
                authors.append(name)

        date_parts = ((item.get("published") or {}).get("date-parts") or [[]])[0]
        publication_year = date_parts[0] if date_parts else None
        venues = item.get("container-title") or []

        return LiteratureCandidate(
            id=uuid5(NAMESPACE_URL, f"crossref:{source_id}"),
            source="crossref",
            source_id=source_id,
            doi=doi,
            title=title,
            authors=authors,
            publication_year=publication_year,
            venue=str(venues[0]).strip() if venues else None,
            url=url,
            work_type=item.get("type"),
        )
