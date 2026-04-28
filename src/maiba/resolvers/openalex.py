"""OpenAlex metadata resolver."""

from __future__ import annotations

import os

from maiba.config import Config
from maiba.model import Item
from maiba.resolvers import ResolutionResult, make_http_client
from maiba.resolvers._scoring import score_candidate


def _api_key() -> str:
    return os.environ.get("OPENALEX_API_KEY", "").strip()


class ResolverRateLimitedError(Exception):
    """Raised when an upstream resolver returns HTTP 429 (rate limited)."""

    def __init__(self, source: str) -> None:
        super().__init__(f"{source} resolver: rate limited (HTTP 429)")
        self.source = source


_OPENALEX_TYPE_TO_RIS: dict[str, str] = {
    "article": "JOUR",
    "book": "BOOK",
    "book-chapter": "CHAP",
    "dataset": "DATA",
    "dissertation": "THES",
    "editorial": "JOUR",
    "erratum": "JOUR",
    "letter": "JOUR",
    "monograph": "BOOK",
    "other": "GEN",
    "paratext": "GEN",
    "peer-review": "JOUR",
    "preprint": "JOUR",
    "reference-entry": "ENCYC",
    "report": "RPRT",
    "review": "JOUR",
    "standard": "STAND",
}


def _reconstruct_abstract(inverted: dict | None) -> str | None:
    if not inverted:
        return None
    pos_to_word: dict[int, str] = {}
    for word, positions in inverted.items():
        for p in positions:
            pos_to_word[p] = word
    if not pos_to_word:
        return None
    return " ".join(pos_to_word[i] for i in sorted(pos_to_word))


def _work_to_item(work: dict) -> Item:
    """Map an OpenAlex Work object to a MAIBA Item."""
    authors = [
        a["author"]["display_name"]
        for a in work.get("authorships", [])
        if a.get("author", {}).get("display_name")
    ]

    doi_raw = work.get("doi") or ""
    doi = doi_raw.removeprefix("https://doi.org/") if doi_raw else None  # noqa: hygiene

    source_name = None
    primary_loc = work.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    source_name = source.get("display_name")
    if not source_name:
        host_venue = work.get("host_venue") or {}
        source_name = host_venue.get("display_name")

    biblio = work.get("biblio") or {}

    keywords = [kw["display_name"] for kw in work.get("keywords", []) if kw.get("display_name")]

    oa_type = work.get("type", "other")
    ris_type = _OPENALEX_TYPE_TO_RIS.get(oa_type, "GEN")

    return Item(
        TY=ris_type,
        TI=work.get("title") or "",
        AU=authors,
        PY=work.get("publication_year"),
        DA=work.get("publication_date"),
        JO=source_name,
        VL=biblio.get("volume"),
        IS=biblio.get("issue"),
        SP=biblio.get("first_page"),
        EP=biblio.get("last_page"),
        DO=doi if doi else None,
        LA=work.get("language"),
        KW=keywords,
        AB=_reconstruct_abstract(work.get("abstract_inverted_index")),
    )


class OpenAlexResolver:
    source: str = "openalex"

    def __init__(self, cfg: Config, *, use_cache: bool = False) -> None:
        self._cfg = cfg
        self._base_url = cfg.resolvers.openalex.base_url
        self._mailto = cfg.contact.mailto
        headers = {"User-Agent": f"MAIBA/0.0 (mailto:{self._mailto})"}
        key = _api_key()
        if key:
            headers["Authorization"] = f"Bearer {key}"
        self._client = make_http_client(cfg.http, headers, use_cache=use_cache)

    def resolve(self, item: Item) -> ResolutionResult | None:
        if item.DO:
            return self._resolve_by_doi(item)
        return self._resolve_by_search(item)

    def _resolve_by_doi(self, item: Item) -> ResolutionResult | None:
        url = f"{self._base_url}/works/doi:{item.DO}"
        resp = self._client.get(url, params={"mailto": self._mailto})
        if resp.status_code == 429:
            raise ResolverRateLimitedError("openalex")
        if resp.status_code != 200:
            return None
        work = resp.json()
        candidate = _work_to_item(work)
        return ResolutionResult(candidate=candidate, confidence=1.0, source="openalex")

    def _resolve_by_search(self, item: Item) -> ResolutionResult | None:
        params: dict[str, str | int] = {
            "search": item.TI,
            "per_page": 5,
            "mailto": self._mailto,
        }
        if item.PY:
            params["filter"] = f"publication_year:{item.PY}"

        url = f"{self._base_url}/works"
        resp = self._client.get(url, params=params)
        if resp.status_code == 429:
            raise ResolverRateLimitedError("openalex")
        if resp.status_code != 200:
            return None

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None

        best_result: ResolutionResult | None = None
        best_confidence = 0.0

        for work in results:
            candidate = _work_to_item(work)
            confidence = score_candidate(item, candidate, self._cfg)
            if confidence is not None and confidence > best_confidence:
                best_confidence = confidence
                best_result = ResolutionResult(
                    candidate=candidate, confidence=confidence, source="openalex"
                )

        return best_result
