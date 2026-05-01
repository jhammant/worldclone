"""End-to-end forecaster pipeline.

flow: question → query generation → news retrieval → relevance ranking →
summarisation → 5-variant ensemble → mean probability
"""
from __future__ import annotations

import asyncio
import logging
import time

from ..common.io import ForecastResult, ManifoldQuestion
from ..common.llm import chat, chat_json
from .prompts import (
    FORECASTER_OUTPUT_SCHEMA,
    FORECASTER_VARIANTS,
    QUERY_GENERATION,
    QUERY_GENERATION_SCHEMA,
    RELEVANCE_BATCH,
    RELEVANCE_SCHEMA,
    SUMMARIZE,
)
from .retrieval import Article, gather_evidence

log = logging.getLogger(__name__)


def _clip_probability(p: float) -> float:
    return max(0.01, min(0.99, float(p)))


async def generate_queries(question: ManifoldQuestion, as_of_date: str, n: int = 4) -> list[str]:
    parsed, _ = await chat_json(
        messages=[
            {"role": "system", "content": "You generate concise web search queries to research forecasting questions."},
            {"role": "user", "content": QUERY_GENERATION.format(
                question=question.question,
                criteria=question.resolution_criteria,
                as_of_date=as_of_date,
                n=n,
            )},
        ],
        schema=QUERY_GENERATION_SCHEMA,
        max_tokens=300,
        reasoning_effort="none",
    )
    return parsed["queries"][:n]


async def rank_articles(
    question: ManifoldQuestion,
    articles: list[Article],
    keep_top: int = 12,
) -> list[Article]:
    """Score articles 0-10 in one batched call; keep top N."""
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
                question=question.question,
                criteria=question.resolution_criteria,
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


async def summarize_article(question: ManifoldQuestion, article: Article) -> str:
    """Tight 2-3 sentence summary focused on the question."""
    if article.source == "timeline":
        # Already a fact; no need to summarize further
        return f"({article.published_date}) {article.text}"
    content, _ = await chat(
        messages=[
            {"role": "system", "content": "You summarize articles tightly for a forecaster."},
            {"role": "user", "content": SUMMARIZE.format(
                question=question.question, article=f"{article.title}\n\n{article.text[:3000]}"
            )},
        ],
        max_tokens=200,
        reasoning_effort="none",
    )
    return f"({article.published_date}) {content.strip()}"


async def ensemble_forecast(
    question: ManifoldQuestion,
    evidence: str,
    as_of_date: str,
) -> tuple[float, list[float], str]:
    """Run all 5 ensemble variants in parallel; return (mean, individual, last_reasoning).

    Uses JSON-schema output for reliability — open-weights models drift on text-format
    requirements, but native LM Studio JSON mode is solid.
    """
    async def one(variant: str, template: str) -> tuple[float, str]:
        prompt = template.format(
            question=question.question,
            criteria=question.resolution_criteria,
            as_of_date=as_of_date,
            evidence=evidence,
        )
        try:
            parsed, _ = await chat_json(
                messages=[
                    {"role": "system", "content": "You are a calibrated forecaster. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
                schema=FORECASTER_OUTPUT_SCHEMA,
                max_tokens=1200,
                reasoning_effort="none",
                temperature=0.7,
            )
            return _clip_probability(parsed["probability"]), parsed.get("reasoning", "")
        except Exception as e:
            log.warning("Forecaster variant %s failed: %s", variant, e)
            return 0.5, f"(variant {variant} failed: {e})"

    coros = [one(name, tmpl) for name, tmpl in FORECASTER_VARIANTS.items()]
    results = await asyncio.gather(*coros)
    probs = [p for p, _ in results]
    mean_prob = sum(probs) / len(probs) if probs else 0.5
    last_reasoning = results[-1][1] if results else ""
    return mean_prob, probs, last_reasoning


async def forecast_question(
    question: ManifoldQuestion,
    as_of_date: str,
    timeline_path: str = "data/iran_timeline.json",
    n_queries: int = 4,
    keep_top: int = 10,
) -> ForecastResult:
    """End-to-end Halawi pipeline for one question."""
    t0 = time.time()
    log.info("Forecasting %s (%s)", question.id, question.question[:80])

    # 1. Query generation (skip if no Exa key — timeline-only mode)
    import os
    has_exa = bool(os.environ.get("EXA_API_KEY", "").strip())
    queries: list[str] = []
    if has_exa:
        queries = await generate_queries(question, as_of_date, n=n_queries)
        log.info("  generated %d queries", len(queries))

    # 2. Retrieval (timeline + Exa if available)
    articles = gather_evidence(queries, as_of_date, timeline_path=timeline_path)
    log.info("  retrieved %d articles", len(articles))

    # 3. Rank (only if more than keep_top)
    if len(articles) > keep_top:
        articles = await rank_articles(question, articles, keep_top=keep_top)

    # 4. Summarize (in parallel; timeline articles short-circuit)
    summaries = await asyncio.gather(*[summarize_article(question, a) for a in articles])
    evidence_block = "\n\n".join(summaries) if summaries else "(no evidence available)"

    # 5. Ensemble forecast
    mean_p, individual, last_reasoning = await ensemble_forecast(question, evidence_block, as_of_date)
    elapsed = time.time() - t0
    log.info("  -> P(YES)=%.3f  individuals=%s  in %.1fs", mean_p, [round(x, 2) for x in individual], elapsed)

    import os as _os
    return ForecastResult(
        question_id=question.id,
        probability=mean_p,
        ensemble_probabilities=individual,
        reasoning=last_reasoning[:4000],
        n_articles_used=len(articles),
        queries=queries,
        model=_os.environ.get("WORLDCLONE_LLM_MODEL", "qwen/qwen3.6-27b"),
        elapsed_seconds=elapsed,
    )
