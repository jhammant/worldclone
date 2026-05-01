"""Sports game forecaster pipeline (Halawi-style)."""
from __future__ import annotations

import asyncio
import logging
import os
import statistics
import time

from ..common.llm import chat, chat_json
from ..forecaster.prompts import RELEVANCE_BATCH, RELEVANCE_SCHEMA, SUMMARIZE
from ..forecaster.retrieval import Article, search_exa
from .prompts import (
    FORECASTER_VARIANTS,
    GAME_OUTPUT_SCHEMA,
    QUERY_GENERATION,
    QUERY_GENERATION_SCHEMA,
    SPORT_LABELS,
)
from .schemas import Game, GameForecast

log = logging.getLogger(__name__)


def _format_game_context(game: Game) -> str:
    lines = []
    if game.is_playoff:
        lines.append(f"Playoff game ({game.series_context})." if game.series_context else "Playoff game.")
    if game.home_record_wins is not None:
        lines.append(f"Home record: {game.home_record_wins}-{game.home_record_losses}")
    if game.away_record_wins is not None:
        lines.append(f"Away record: {game.away_record_wins}-{game.away_record_losses}")
    if game.vegas_home_moneyline is not None:
        lines.append(f"Vegas moneyline: home {game.vegas_home_moneyline:+d} / away {game.vegas_away_moneyline:+d}")
    if game.vegas_spread is not None:
        sign = "+" if game.vegas_spread > 0 else ""
        lines.append(f"Vegas spread: home {sign}{game.vegas_spread} | total {game.vegas_total}")
    if game.venue:
        lines.append(f"Venue: {game.venue}")
    if game.notes:
        lines.append(f"Notes: {game.notes}")
    return "\n".join(lines) if lines else "(no structured pre-game info)"


async def generate_queries(game: Game, as_of_date: str, n: int = 4) -> list[str]:
    parsed, _ = await chat_json(
        messages=[
            {"role": "system", "content": "You generate concise web search queries for sports forecasting."},
            {"role": "user", "content": QUERY_GENERATION.format(
                home_team=game.home_team, away_team=game.away_team,
                sport_label=SPORT_LABELS.get(game.sport, game.sport.upper()),
                game_date=game.game_date,
                context=_format_game_context(game),
                as_of_date=as_of_date, n=n,
            )},
        ],
        schema=QUERY_GENERATION_SCHEMA,
        max_tokens=300,
        reasoning_effort="none",
    )
    return parsed["queries"][:n]


async def gather_evidence(queries: list[str], as_of_date: str, num_per_query: int = 8) -> list[Article]:
    seen: set[str] = set()
    out: list[Article] = []
    for q in queries:
        for a in search_exa(q, as_of_date, num=num_per_query):
            if a.url in seen:
                continue
            seen.add(a.url)
            out.append(a)
    return out


async def rank_articles(game: Game, articles: list[Article], keep_top: int = 12) -> list[Article]:
    if len(articles) <= keep_top:
        return articles
    block = "\n\n".join(
        f"[{i}] ({a.published_date}) {a.title}\n{a.text[:400]}"
        for i, a in enumerate(articles)
    )
    parsed, _ = await chat_json(
        messages=[
            {"role": "system", "content": "You rate article relevance to a sports forecasting question."},
            {"role": "user", "content": RELEVANCE_BATCH.format(
                question=f"{game.away_team} at {game.home_team} on {game.game_date}",
                criteria="The article should help forecast which team wins and by how much: form, injuries, lines, matchups.",
                articles_block=block,
            )},
        ],
        schema=RELEVANCE_SCHEMA, max_tokens=600, reasoning_effort="none",
    )
    scores = {s["index"]: s["score"] for s in parsed["scores"]}
    scored = [(scores.get(i, 0), a) for i, a in enumerate(articles)]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in scored[:keep_top]]


async def summarize_article(game: Game, article: Article) -> str:
    content, _ = await chat(
        messages=[
            {"role": "system", "content": "You tightly summarize articles for a sports forecaster."},
            {"role": "user", "content": SUMMARIZE.format(
                question=f"{game.away_team} at {game.home_team} ({game.game_date})",
                article=f"{article.title}\n\n{article.text[:3000]}",
            )},
        ],
        max_tokens=200, reasoning_effort="none",
    )
    return f"({article.published_date}) {content.strip()}"


async def ensemble_forecast(game: Game, evidence: str, as_of_date: str) -> dict:
    context = _format_game_context(game)

    async def one(name: str, template: str) -> dict | None:
        prompt = template.format(
            home_team=game.home_team, away_team=game.away_team,
            sport_label=SPORT_LABELS.get(game.sport, game.sport.upper()),
            game_date=game.game_date, context=context, evidence=evidence,
        )
        try:
            parsed, _ = await chat_json(
                messages=[
                    {"role": "system", "content": "You are a sharp sports bettor. Output JSON only."},
                    {"role": "user", "content": prompt},
                ],
                schema=GAME_OUTPUT_SCHEMA, max_tokens=900, reasoning_effort="none", temperature=0.7,
            )
            return parsed
        except Exception as e:
            log.warning("Variant %s failed: %s", name, e)
            return None

    results = await asyncio.gather(*[one(n, t) for n, t in FORECASTER_VARIANTS.items()])
    valid = [r for r in results if r is not None]
    if not valid:
        return {"p_home": 0.5, "margin": 0.0, "total": 0.0, "individual_p": [], "individual_margin": [], "reasoning": ""}

    ps = [max(0.01, min(0.99, float(r["p_home_win"]))) for r in valid]
    ms = [float(r["predicted_margin_home"]) for r in valid]
    ts = [float(r.get("predicted_total") or 0.0) for r in valid if r.get("predicted_total")]
    return {
        "p_home": float(statistics.mean(ps)),
        "margin": float(statistics.median(ms)),
        "total": float(statistics.mean(ts)) if ts else 0.0,
        "individual_p": ps,
        "individual_margin": ms,
        "reasoning": valid[-1].get("reasoning", ""),
    }


async def forecast_game(game: Game, as_of_date: str, n_queries: int = 4, keep_top: int = 10) -> GameForecast:
    t0 = time.time()
    log.info("Forecasting %s — %s @ %s on %s", game.id, game.away_team, game.home_team, game.game_date)

    has_exa = bool(os.environ.get("EXA_API_KEY", "").strip())
    queries: list[str] = []
    articles: list[Article] = []
    if has_exa:
        queries = await generate_queries(game, as_of_date, n=n_queries)
        log.info("  generated %d queries", len(queries))
        articles = await gather_evidence(queries, as_of_date)
        log.info("  retrieved %d articles", len(articles))

    if len(articles) > keep_top:
        articles = await rank_articles(game, articles, keep_top=keep_top)

    summaries = await asyncio.gather(*[summarize_article(game, a) for a in articles]) if articles else []
    evidence_block = "\n\n".join(summaries) if summaries else "(no retrieved evidence — relying on training-data prior)"

    out = await ensemble_forecast(game, evidence_block, as_of_date)
    elapsed = time.time() - t0
    log.info("  -> P(home)=%.3f margin=%.1f total=%.1f in %.1fs",
             out["p_home"], out["margin"], out["total"], elapsed)

    return GameForecast(
        game_id=game.id,
        p_home_win=out["p_home"],
        predicted_margin_home=out["margin"],
        predicted_total=out["total"] or None,
        ensemble_p_home=out["individual_p"],
        ensemble_margin=out["individual_margin"],
        reasoning=out["reasoning"][:4000],
        n_articles_used=len(articles),
        queries=queries,
        model=os.environ.get("WORLDCLONE_LLM_MODEL", "qwen/qwen3.6-27b"),
        elapsed_seconds=elapsed,
        as_of_date=as_of_date,
    )
