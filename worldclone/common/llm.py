"""Local LLM wrapper for LM Studio + Qwen 3.6 27B.

- OpenAI-compatible endpoint (default localhost:1234/v1)
- parallel=2 semaphore (matches LM Studio config)
- reasoning_effort defaults to "none" (Qwen thinking mode is too slow for our use)
- JSON-schema mode supported natively
- Per-call timing accounting + runtime kill switch
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field

import httpx

log = logging.getLogger(__name__)


def _env(key: str, default: str | None = None) -> str:
    val = os.environ.get(key, default)
    if val is None:
        raise RuntimeError(f"Missing env var: {key}")
    return val


@dataclass
class Usage:
    """Per-call accounting."""
    wall_seconds: float
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    model: str

    @property
    def content_tokens(self) -> int:
        return self.completion_tokens - self.reasoning_tokens


@dataclass
class RuntimeAccountant:
    """Tracks total wall time across calls; aborts if budget exceeded."""
    max_runtime_hours: float
    started_at: float = field(default_factory=time.time)
    total_call_seconds: float = 0.0
    total_calls: int = 0
    usages: list[Usage] = field(default_factory=list)

    def record(self, u: Usage) -> None:
        self.total_call_seconds += u.wall_seconds
        self.total_calls += 1
        self.usages.append(u)

        # Budget check on wall-clock since start (not just call time)
        elapsed_hours = (time.time() - self.started_at) / 3600
        if elapsed_hours > self.max_runtime_hours:
            raise RuntimeError(
                f"Runtime budget exceeded: {elapsed_hours:.2f}h > {self.max_runtime_hours}h "
                f"after {self.total_calls} calls"
            )

    def summary(self) -> dict:
        elapsed = time.time() - self.started_at
        ct = sum(u.content_tokens for u in self.usages)
        rt = sum(u.reasoning_tokens for u in self.usages)
        pt = sum(u.prompt_tokens for u in self.usages)
        return {
            "elapsed_seconds": elapsed,
            "total_calls": self.total_calls,
            "total_call_seconds": self.total_call_seconds,
            "prompt_tokens": pt,
            "content_tokens": ct,
            "reasoning_tokens": rt,
            "tokens_per_second": (ct + rt) / self.total_call_seconds if self.total_call_seconds else 0,
        }


# Module-level singletons
_accountant: RuntimeAccountant | None = None
_semaphore: asyncio.Semaphore | None = None
_client: httpx.AsyncClient | None = None


def init(
    *,
    max_runtime_hours: float | None = None,
    parallel: int | None = None,
) -> RuntimeAccountant:
    """Initialize global LLM state. Call once at process start."""
    global _accountant, _semaphore, _client
    max_h = max_runtime_hours or float(os.environ.get("WORLDCLONE_MAX_RUNTIME_HOURS", "10"))
    par = parallel or int(os.environ.get("WORLDCLONE_LLM_PARALLEL", "2"))
    _accountant = RuntimeAccountant(max_runtime_hours=max_h)
    _semaphore = asyncio.Semaphore(par)
    _client = httpx.AsyncClient(
        base_url=_env("WORLDCLONE_LLM_BASE_URL", "http://localhost:1234/v1"),
        timeout=httpx.Timeout(300.0, connect=10.0),
        headers={"Content-Type": "application/json"},
    )
    log.info("LLM init: parallel=%d max_runtime_hours=%.1f", par, max_h)
    return _accountant


def accountant() -> RuntimeAccountant:
    if _accountant is None:
        init()
    assert _accountant is not None
    return _accountant


async def chat(
    *,
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 800,
    temperature: float = 0.7,
    reasoning_effort: str | None = None,
    json_schema: dict | None = None,
    schema_name: str = "out",
) -> tuple[str, Usage]:
    """Single chat completion. Returns (content, usage).

    json_schema: if provided, enforces JSON-schema output via response_format.
    reasoning_effort: "none" | "low" | "medium" | "high". Default from env, falls back to "none".
    """
    if _client is None or _semaphore is None:
        init()
    assert _client is not None and _semaphore is not None

    model = model or _env("WORLDCLONE_LLM_MODEL", "qwen/qwen3.6-27b")
    reasoning_effort = reasoning_effort or os.environ.get("WORLDCLONE_LLM_REASONING_DEFAULT", "none")

    body: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "reasoning_effort": reasoning_effort,
    }
    if json_schema is not None:
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {"name": schema_name, "schema": json_schema},
        }

    # Retry on transient HTTP errors (LM Studio occasionally returns 500 when
    # several requests fan out at once, even with a semaphore — the backoff
    # spaces them out enough to clear).
    last_exc: Exception | None = None
    data: dict = {}
    dt = 0.0
    async with _semaphore:
        for attempt in range(4):  # up to 4 attempts: 0, 0.5s, 1.5s, 4s backoff
            try:
                t0 = time.time()
                resp = await _client.post("/chat/completions", json=body)
                dt = time.time() - t0
                resp.raise_for_status()
                data = resp.json()
                break
            except (httpx.HTTPStatusError, httpx.HTTPError) as e:
                last_exc = e
                status = getattr(getattr(e, "response", None), "status_code", None)
                # 5xx is retryable; 4xx (except 429) is usually a permanent error
                if status is not None and 400 <= status < 500 and status != 429:
                    log.error("non-retryable HTTP %d: %s", status, e)
                    raise
                wait = 0.5 * (3 ** attempt)
                log.warning("LLM call failed (attempt %d/4, status=%s): %s — retrying in %.1fs", attempt + 1, status, e, wait)
                await asyncio.sleep(wait)
        else:
            assert last_exc is not None
            raise last_exc

    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    u = data.get("usage", {})
    rt = u.get("completion_tokens_details", {}).get("reasoning_tokens", 0) if "completion_tokens_details" in u else 0
    usage = Usage(
        wall_seconds=dt,
        prompt_tokens=u.get("prompt_tokens", 0),
        completion_tokens=u.get("completion_tokens", 0),
        reasoning_tokens=rt,
        model=model,
    )
    accountant().record(usage)
    log.debug("chat call: %.2fs %d/%d toks", dt, usage.content_tokens, usage.completion_tokens)
    return content, usage


async def chat_json(
    *,
    messages: list[dict],
    schema: dict,
    schema_name: str = "out",
    retries: int = 2,
    **kwargs,
) -> tuple[dict, Usage]:
    """Chat with JSON-schema enforcement. Retries on parse failure.

    Returns (parsed_dict, usage).
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        content, usage = await chat(
            messages=messages,
            json_schema=schema,
            schema_name=schema_name,
            **kwargs,
        )
        try:
            return json.loads(content), usage
        except json.JSONDecodeError as e:
            last_exc = e
            log.warning("JSON parse failed (attempt %d/%d): %s | raw=%r", attempt + 1, retries + 1, e, content[:200])
            if attempt < retries:
                # Add a corrective system message and retry
                messages = messages + [
                    {"role": "assistant", "content": content},
                    {"role": "user", "content": "That output was not valid JSON. Please respond with ONLY valid JSON matching the schema, no other text."},
                ]
    assert last_exc is not None
    raise last_exc


async def gather_chat(calls: list[dict]) -> list[tuple[str, Usage]]:
    """Run multiple chat calls concurrently (bounded by the semaphore)."""
    return await asyncio.gather(*[chat(**c) for c in calls])
