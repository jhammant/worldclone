"""News retrieval with Exa.ai (primary) + timeline-fallback for offline pilot.

Exa supports `endPublishedDate` in ISO 8601 — the cleanest way to enforce a
strict pre-resolution cutoff. Without an API key we fall back to using the
hand-curated timeline facts as evidence, which is symmetrically available to
the simulation so it doesn't bias the comparison.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    url: str
    published_date: str  # YYYY-MM-DD
    text: str
    source: str = "exa"
    score: float = 0.0


def _cache_path(query: str, before_date: str) -> Path:
    cache_dir = Path(os.environ.get("WORLDCLONE_CACHE_DIR", "./data/cache")) / "news"
    cache_dir.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(f"{query}|{before_date}".encode()).hexdigest()[:16]
    return cache_dir / f"{h}.json"


def search_exa(query: str, before_date: str, num: int = 10) -> list[Article]:
    """Cached Exa.ai search with strict end-published-date filter."""
    cache_file = _cache_path(query, before_date)
    if cache_file.exists():
        with cache_file.open() as f:
            raw = json.load(f)
        return [Article(**a) for a in raw]

    api_key = os.environ.get("EXA_API_KEY", "").strip()
    if not api_key:
        log.warning("EXA_API_KEY not set; returning no Exa results for %r", query)
        cache_file.write_text("[]")
        return []

    from exa_py import Exa  # type: ignore[import-not-found]

    exa = Exa(api_key=api_key)
    end_iso = f"{before_date}T23:59:59.000Z"
    try:
        result = exa.search_and_contents(
            query=query,
            type="auto",
            num_results=num,
            end_published_date=end_iso,
            text=True,
        )
    except Exception as e:
        log.error("Exa search failed for %r: %s", query, e)
        return []

    articles = []
    n_dropped_no_date = 0
    n_dropped_post_cutoff = 0
    for r in getattr(result, "results", []):
        published_date = (getattr(r, "published_date", "") or "")[:10]
        # CRITICAL: enforce date cutoff defensively — Exa's endPublishedDate is
        # only a request hint and frequently returns dateless evergreen pages
        # (e.g. Box Office Mojo) that contain post-release figures and would
        # leak ground truth into the forecaster.
        if not published_date:
            n_dropped_no_date += 1
            continue
        if published_date > before_date:
            n_dropped_post_cutoff += 1
            continue
        articles.append(Article(
            title=getattr(r, "title", "") or "",
            url=getattr(r, "url", "") or "",
            published_date=published_date,
            text=(getattr(r, "text", "") or "")[:6000],
            source="exa",
            score=float(getattr(r, "score", 0.0) or 0.0),
        ))
    if n_dropped_no_date or n_dropped_post_cutoff:
        log.info("Exa date-filter: dropped %d dateless, %d post-cutoff (kept %d) for %r before %s",
                 n_dropped_no_date, n_dropped_post_cutoff, len(articles), query[:50], before_date)
    cache_file.write_text(json.dumps([a.__dict__ for a in articles]))
    return articles


def timeline_as_articles(timeline_path: str | Path, before_date: str) -> list[Article]:
    """Fallback evidence: use the curated timeline facts as 'articles'.

    Each fact becomes a fake article so the rest of the pipeline is unchanged.
    Filters to facts on or before `before_date`.
    """
    with Path(timeline_path).open() as f:
        timeline = json.load(f)
    out: list[Article] = []
    for fact in timeline.get("facts", []):
        if fact["date"] <= before_date:
            out.append(Article(
                title=f"Timeline fact: {fact['date']}",
                url=f"timeline://{fact['date']}",
                published_date=fact["date"],
                text=fact["fact"],
                source="timeline",
            ))
    return out


def gather_evidence(
    queries: list[str],
    before_date: str,
    timeline_path: str | Path = "data/iran_timeline.json",
    num_per_query: int = 8,
) -> list[Article]:
    """Aggregate Exa results across queries, deduplicate by URL.
    Always include the timeline as a baseline evidence source.
    """
    seen_urls: set[str] = set()
    out: list[Article] = []

    # Always include timeline facts (cheap + symmetric across both pipelines)
    for a in timeline_as_articles(timeline_path, before_date):
        if a.url in seen_urls:
            continue
        seen_urls.add(a.url)
        out.append(a)

    # Exa results
    for q in queries:
        for a in search_exa(q, before_date, num=num_per_query):
            if a.url in seen_urls:
                continue
            seen_urls.add(a.url)
            out.append(a)
    return out
