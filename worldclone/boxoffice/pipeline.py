"""End-to-end box office forecaster pipeline.

flow: film → query generation → news retrieval → relevance ranking →
summarisation → 5-variant ensemble → median point + 80% CI
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import statistics
import time

from ..common.llm import chat, chat_json
from ..forecaster.prompts import RELEVANCE_BATCH, RELEVANCE_SCHEMA, SUMMARIZE
from ..forecaster.retrieval import Article, search_exa
from .prompts import (
    FORECAST_OUTPUT_SCHEMA,
    FORECASTER_VARIANTS,
    QUERY_GENERATION,
    QUERY_GENERATION_SCHEMA,
)
from .schemas import Film, FilmForecast

log = logging.getLogger(__name__)


def _format_film_block(film: Film) -> str:
    """Build a structured info block for the prompts."""
    lines = []
    if film.distributor:
        lines.append(f"Distributor: {film.distributor}")
    if film.studio:
        lines.append(f"Studio: {film.studio}")
    if film.director:
        lines.append(f"Director: {film.director}")
    if film.cast:
        lines.append(f"Cast: {', '.join(film.cast[:6])}")
    if film.genre:
        lines.append(f"Genre: {', '.join(film.genre)}")
    if film.rating:
        lines.append(f"Rating: {film.rating}")
    if film.runtime_minutes:
        lines.append(f"Runtime: {film.runtime_minutes} min")
    if film.franchise:
        lines.append(f"Franchise: {film.franchise}")
    if film.sequel_number is not None:
        lines.append(f"Sequel #: {film.sequel_number}")
    if film.budget_usd:
        lines.append(f"Production budget (reported): ${film.budget_usd:,}")
    if film.opening_theater_count:
        lines.append(f"Opening theater count: {film.opening_theater_count:,}")
    if film.rotten_tomatoes_score is not None:
        lines.append(f"Rotten Tomatoes (Tomatometer): {film.rotten_tomatoes_score}%")
    if film.metacritic_score is not None:
        lines.append(f"Metacritic: {film.metacritic_score}")

    # Leading indicators — present these prominently if available
    leading = []
    if getattr(film, "thursday_previews_usd", None) is not None:
        leading.append(f"Thursday previews: ${film.thursday_previews_usd:,}")
    if getattr(film, "presales_signal", ""):
        leading.append(f"Pre-sale tracking signal: {film.presales_signal}")
    if getattr(film, "trailer_youtube_views", None) is not None:
        leading.append(f"Main trailer YouTube views (cumulative at as-of date): {film.trailer_youtube_views:,}")
    if getattr(film, "social_buzz_note", ""):
        leading.append(f"Social buzz signal: {film.social_buzz_note}")
    if leading:
        lines.append("LEADING INDICATORS:")
        for li in leading:
            lines.append(f"  - {li}")

    # Franchise priors — give the bot historical comparables when known
    fp = getattr(film, "franchise_priors", []) or []
    if fp:
        lines.append("Franchise prior films:")
        for p in fp[:5]:
            ow = p.get("opening_weekend_usd")
            ow_s = f" — opening ${ow/1e6:.1f}M" if ow else ""
            lines.append(f"  - {p.get('title','?')} ({p.get('release_date','?')}){ow_s}")

    if film.notes:
        notes = _scrub_ground_truth_from_text(film.notes)
        if notes:
            lines.append(f"Notes: {notes}")
    return "\n".join(lines) if lines else "(no structured details available)"


_SCRUB_PATTERNS = [
    # Markers that obviously precede an actual number
    (re.compile(r"(ACTUALS?:|Actual opening|ACTUAL OPENING).*", re.IGNORECASE), ""),
    # Dollar amounts with million/m suffix
    (re.compile(r"\$\s*[\d.,]+\s*(?:million|m\b)", re.IGNORECASE), "[REDACTED]"),
    # Bare large dollar amounts
    (re.compile(r"\$\s*[\d,]{4,}"), "[REDACTED]"),
    # Phrases that imply post-release knowledge
    (re.compile(r"\b(?:franchise-?best|record-setting|\d-day\s+(?:debut|opening))\b[^.;]*", re.IGNORECASE), ""),
    (re.compile(r"\b(?:debuted|opened)\s+(?:to|with)[^.;]*", re.IGNORECASE), ""),
    (re.compile(r"opening\s+weekend\s+(?:gross|box\s+office)[^.;]*", re.IGNORECASE), ""),
]


def _scrub_ground_truth_from_text(text: str) -> str:
    """Strip patterns that smell like leaked actuals from arbitrary text.

    Used on the `notes` field before passing to the LLM to prevent self-leakage
    when candidates.json has been populated with post-release outcome figures.
    """
    out = text
    for pat, repl in _SCRUB_PATTERNS:
        out = pat.sub(repl, out)
    # Drop sentences containing the redaction marker
    sentences = re.split(r"(?<=[.;|])\s+", out)
    sentences = [s for s in sentences if "[REDACTED]" not in s]
    out = " ".join(s.strip() for s in sentences)
    return re.sub(r"\s+", " ", out).strip(" |;,.")


async def generate_queries(film: Film, as_of_date: str, n: int = 4) -> list[str]:
    parsed, _ = await chat_json(
        messages=[
            {"role": "system", "content": "You generate concise web search queries for box office research."},
            {"role": "user", "content": QUERY_GENERATION.format(
                title=film.title,
                release_date=film.release_date,
                distributor=film.distributor or "(unknown)",
                notes=film.notes or "(none)",
                as_of_date=as_of_date,
                n=n,
            )},
        ],
        schema=QUERY_GENERATION_SCHEMA,
        max_tokens=300,
        reasoning_effort="none",
    )
    return parsed["queries"][:n]


async def gather_film_evidence(
    queries: list[str],
    as_of_date: str,
    num_per_query: int = 8,
) -> list[Article]:
    """Aggregate Exa results across queries; deduplicate by URL.

    No timeline-fallback for box office — without an Exa key the forecaster
    runs on its training-data prior alone, which is fine but flagged.
    """
    seen: set[str] = set()
    out: list[Article] = []
    for q in queries:
        for a in search_exa(q, as_of_date, num=num_per_query):
            if a.url in seen:
                continue
            seen.add(a.url)
            out.append(a)
    return out


async def rank_articles(film: Film, articles: list[Article], keep_top: int = 12) -> list[Article]:
    if len(articles) <= keep_top:
        return articles
    block_lines = []
    for i, a in enumerate(articles):
        block_lines.append(f"[{i}] ({a.published_date}) {a.title}\n{a.text[:400]}")
    block = "\n\n".join(block_lines)

    parsed, _ = await chat_json(
        messages=[
            {"role": "system", "content": "You rate the relevance of articles to a forecasting question."},
            {"role": "user", "content": RELEVANCE_BATCH.format(
                question=f"Opening weekend box office for: {film.title} ({film.release_date})",
                criteria="The article should help estimate domestic opening-weekend gross — tracking projections, comparable films, reviews, theater count, marketing buzz.",
                articles_block=block,
            )},
        ],
        schema=RELEVANCE_SCHEMA,
        max_tokens=600,
        reasoning_effort="none",
    )
    scores = {s["index"]: s["score"] for s in parsed["scores"]}
    scored = [(scores.get(i, 0), a) for i, a in enumerate(articles)]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:keep_top]]


async def summarize_article(film: Film, article: Article) -> str:
    content, _ = await chat(
        messages=[
            {"role": "system", "content": "You summarize articles tightly for a box office forecaster."},
            {"role": "user", "content": SUMMARIZE.format(
                question=f"Opening weekend gross for {film.title} ({film.release_date})",
                article=f"{article.title}\n\n{article.text[:3000]}",
            )},
        ],
        max_tokens=200,
        reasoning_effort="none",
    )
    return f"({article.published_date}) {content.strip()}"


async def ensemble_forecast(
    film: Film,
    evidence: str,
    as_of_date: str,
) -> tuple[int, int, int, list[int], str]:
    """Run all 5 variants in parallel, aggregate.

    Returns (median_point_estimate, ci_low, ci_high, individual_points, last_reasoning).
    Aggregation: median of point estimates (robust to outlier variants),
    union of CIs (10th percentile of all lows, 90th percentile of all highs).
    """
    film_block = _format_film_block(film)

    async def one(name: str, template: str) -> tuple[dict, str]:
        prompt = template.format(
            title=film.title,
            release_date=film.release_date,
            distributor=film.distributor or "(unknown)",
            film_block=film_block,
            evidence=evidence,
        )
        try:
            parsed, _ = await chat_json(
                messages=[
                    {"role": "system", "content": "You are a box office analyst. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
                schema=FORECAST_OUTPUT_SCHEMA,
                max_tokens=1200,
                reasoning_effort="none",
                temperature=0.7,
            )
            return parsed, name
        except Exception as e:
            log.warning("Variant %s failed: %s", name, e)
            return {"point_estimate_usd": 0, "ci_low_usd": 0, "ci_high_usd": 0, "reasoning": f"(variant {name} failed: {e})"}, name

    results = await asyncio.gather(*[one(n, t) for n, t in FORECASTER_VARIANTS.items()])

    # Filter out failed variants (point=0)
    valid = [(p, n) for p, n in results if p["point_estimate_usd"] > 0]
    if not valid:
        log.error("All variants failed for %s", film.id)
        return 0, 0, 0, [], ""

    points = [int(p["point_estimate_usd"]) for p, _ in valid]
    lows = [int(p["ci_low_usd"]) for p, _ in valid]
    highs = [int(p["ci_high_usd"]) for p, _ in valid]

    median_point = int(statistics.median(points))
    # Use min low / max high to widen CI by ensemble disagreement
    ci_low = min(lows)
    ci_high = max(highs)
    last_reasoning = valid[-1][0]["reasoning"]

    return median_point, ci_low, ci_high, points, last_reasoning


async def forecast_film(
    film: Film,
    as_of_date: str,
    n_queries: int = 4,
    keep_top: int = 10,
) -> FilmForecast:
    t0 = time.time()
    log.info("Forecasting film %s — %s (release %s)", film.id, film.title, film.release_date)

    # 1. Query generation (skipped if no Exa key)
    has_exa = bool(os.environ.get("EXA_API_KEY", "").strip())
    queries: list[str] = []
    articles: list[Article] = []
    if has_exa:
        queries = await generate_queries(film, as_of_date, n=n_queries)
        log.info("  generated %d queries", len(queries))
        articles = await gather_film_evidence(queries, as_of_date)
        log.info("  retrieved %d articles", len(articles))

    # 2. Rank if needed
    if len(articles) > keep_top:
        articles = await rank_articles(film, articles, keep_top=keep_top)

    # 3. Summarize (parallel; no-ops gracefully if articles empty)
    summaries = await asyncio.gather(*[summarize_article(film, a) for a in articles]) if articles else []
    if not summaries:
        evidence_block = "(no retrieved evidence — relying on training-data prior; flag this in reasoning)"
    else:
        evidence_block = "\n\n".join(summaries)

    # 4. Ensemble
    median, lo, hi, individuals, last_reasoning = await ensemble_forecast(film, evidence_block, as_of_date)
    elapsed = time.time() - t0
    log.info("  -> point=$%s (%dM), 80%% CI=[$%dM, $%dM] in %.1fs",
             f"{median:,}", median // 1_000_000, lo // 1_000_000, hi // 1_000_000, elapsed)

    return FilmForecast(
        film_id=film.id,
        point_estimate_usd=median,
        ci_low_usd=lo,
        ci_high_usd=hi,
        ensemble_estimates=individuals,
        reasoning=last_reasoning[:4000],
        n_articles_used=len(articles),
        queries=queries,
        model=os.environ.get("WORLDCLONE_LLM_MODEL", "qwen/qwen3.6-27b"),
        elapsed_seconds=elapsed,
        as_of_date=as_of_date,
    )
