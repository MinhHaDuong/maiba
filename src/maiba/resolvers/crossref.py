"""Crossref metadata resolver."""

from __future__ import annotations

import re
from urllib.parse import quote

from maiba.config import Config
from maiba.model import Item
from maiba.resolvers import ResolutionResult, make_http_client
from maiba.resolvers._scoring import score_candidate

_CROSSREF_TYPE_TO_RIS = {
    "journal-article": "JOUR",
    "book": "BOOK",
    "book-chapter": "CHAP",
    "proceedings-article": "CPAPER",
    "report": "RPRT",
    "dissertation": "THES",
    "dataset": "DATA",
    "monograph": "BOOK",
    "posted-content": "UNPB",
}


class CrossrefResolver:
    def __init__(self, cfg: Config, *, use_cache: bool = False) -> None:
        self._cfg = cfg
        self._base_url = cfg.resolvers.crossref.base_url
        headers = {"User-Agent": f"MAIBA/0.0 (mailto:{cfg.contact.mailto})"}
        self._client = make_http_client(cfg.http, headers, use_cache=use_cache)

    def resolve(self, item: Item) -> ResolutionResult | None:
        if item.DO:
            return self._resolve_by_doi(item)
        return self._resolve_by_search(item)

    def _resolve_by_doi(self, item: Item) -> ResolutionResult | None:
        url = f"{self._base_url}/works/{quote(item.DO, safe='/:')}"
        resp = self._client.get(url)
        if resp.status_code != 200:
            return None
        data = resp.json()
        work = data.get("message", {})
        candidate = _work_to_item(work)
        return ResolutionResult(candidate=candidate, confidence=1.0, source="crossref")

    def _resolve_by_search(self, item: Item) -> ResolutionResult | None:
        params: dict[str, str | int] = {"rows": 5}
        if item.TI:
            params["query.title"] = item.TI
        if item.AU:
            params["query.author"] = item.AU[0]

        resp = self._client.get(f"{self._base_url}/works", params=params)
        if resp.status_code != 200:
            return None

        data = resp.json()
        items = data.get("message", {}).get("items", [])
        if not items:
            return None

        best_result: ResolutionResult | None = None
        best_confidence = 0.0

        for work in items:
            candidate = _work_to_item(work)
            confidence = score_candidate(item, candidate, self._cfg)
            if confidence is not None and confidence > best_confidence:
                best_confidence = confidence
                best_result = ResolutionResult(
                    candidate=candidate, confidence=confidence, source="crossref"
                )

        return best_result


def _work_to_item(work: dict) -> Item:
    title = _extract_title(work)
    authors = _extract_authors(work)
    year = _extract_year(work)
    page = work.get("page", "")
    sp, ep = _split_page(page)

    return Item(
        TY=_CROSSREF_TYPE_TO_RIS.get(work.get("type", ""), "GEN"),
        TI=title,
        AU=authors,
        PY=year,
        JO=_first_or_none(work.get("container-title")),
        VL=work.get("volume"),
        IS=work.get("issue"),
        SP=sp,
        EP=ep,
        DO=work.get("DOI"),
        UR=work.get("URL"),
        LA=work.get("language"),
        KW=work.get("subject") or [],
        AB=_strip_html(work.get("abstract")),
        PB=work.get("publisher"),
    )


def _extract_title(work: dict) -> str:
    titles = work.get("title", [])
    title = titles[0] if titles else ""
    subtitles = work.get("subtitle", [])
    if subtitles and subtitles[0]:
        title = f"{title}: {subtitles[0]}"
    return title


def _extract_authors(work: dict) -> list[str]:
    authors = []
    for a in work.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        if family and given:
            authors.append(f"{family}, {given}")
        elif family:
            authors.append(family)
        elif a.get("name"):
            authors.append(a["name"])
    return authors


def _extract_year(work: dict) -> int | None:
    for key in ("published-print", "published-online", "issued", "created"):
        date_obj = work.get(key)
        if date_obj and "date-parts" in date_obj:
            parts = date_obj["date-parts"]
            if parts and parts[0] and parts[0][0]:
                return int(parts[0][0])
    return None


def _split_page(page: str) -> tuple[str | None, str | None]:
    if not page:
        return None, None
    parts = page.split("-", 1)
    sp = parts[0].strip() or None
    ep = parts[1].strip() if len(parts) > 1 else None
    return sp, ep


def _first_or_none(lst: list | None) -> str | None:
    if lst:
        return lst[0]
    return None


def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"<[^>]+>", "", text).strip() or None
