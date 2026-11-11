import httpx

from app.adapters.crossref_search import CrossrefLiteratureSearch
from app.domain.evidence import SearchPlanContent


def test_crossref_search_maps_metadata_and_deduplicates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/works"
        assert request.url.params["query.bibliographic"] == "cognitive workload error rate"
        assert request.url.params["rows"] == "10"
        assert request.url.params["filter"] == (
            "from-pub-date:2015-01-01,until-pub-date:2026-12-31"
        )
        assert "abstract" not in request.url.params["select"].lower()
        item = {
            "DOI": "10.1234/Example",
            "title": ["Workload and human error"],
            "author": [{"given": "Ada", "family": "Liu"}],
            "published": {"date-parts": [[2024, 5, 1]]},
            "container-title": ["Human Factors"],
            "URL": "https://doi.org/10.1234/example",
            "type": "journal-article",
        }
        return httpx.Response(200, json={"message": {"items": [item, item]}})

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://api.crossref.org/v1",
    )
    search = CrossrefLiteratureSearch(client=client)

    results = search.search(
        SearchPlanContent(
            query="cognitive workload error rate",
            keywords=["cognitive workload", "human error", "error rate"],
            inclusion_criteria=["Empirical study"],
            exclusion_criteria=["Editorial"],
            from_year=2015,
            until_year=2026,
            max_results=10,
        )
    )

    assert len(results) == 1
    assert results[0].doi == "10.1234/example"
    assert results[0].authors == ["Ada Liu"]
    assert results[0].publication_year == 2024
