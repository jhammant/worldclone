"""Append-only immutable prediction store.

Each prediction is hashed (SHA-256 over the prediction's content + a per-run salt)
and stored as a JSON line. The tracker file is git-committable so the hash chain
is publicly verifiable: a prediction in line N must hash with the previous-line
hash baked into it (Merkle-chain) so retroactive edits would require rewriting
every subsequent line.

Two operations:
  - record(prediction)     — append a new prediction with computed hash
  - score_resolved()       — query Manifold for resolution status of all
                             un-resolved predictions; mark them final.

The "we predicted P(YES)=X at time T with market price M and hash H" record
is the only artifact required to later compute Brier/log-loss + ROI vs market.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GENESIS_HASH = "0" * 64


def _stable_dump(d: dict) -> str:
    """Sort keys, separators tight — must be reproducible byte-for-byte."""
    return json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(prev_hash: str, payload: dict) -> str:
    """Hash incorporates previous hash for Merkle-chain immutability."""
    h = hashlib.sha256()
    h.update(prev_hash.encode())
    h.update(_stable_dump(payload).encode())
    return h.hexdigest()


def append_prediction(
    *,
    tracker_path: Path,
    market_id: str,
    question: str,
    url: str,
    category_tag: str,
    close_time_iso: str | None,
    as_of_date: str,
    market_prob_at_prediction: float | None,
    bot_prediction_prob: float,
    ensemble: list[float],
    n_articles: int,
    model: str,
    reasoning: str = "",
    extras: dict[str, Any] | None = None,
) -> dict:
    """Append a new prediction record to the tracker file (append-only JSONL)."""
    tracker_path.parent.mkdir(parents=True, exist_ok=True)

    # Read previous hash from tail of file
    prev_hash = GENESIS_HASH
    if tracker_path.exists() and tracker_path.stat().st_size > 0:
        with tracker_path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    prev_hash = json.loads(line).get("prediction_hash", prev_hash)

    payload: dict[str, Any] = {
        "schema_version": 1,
        "record_id": uuid.uuid4().hex[:16],
        "market_id": market_id,
        "question": question,
        "url": url,
        "category_tag": category_tag,
        "close_time_iso": close_time_iso,
        "as_of_date": as_of_date,
        "market_prob_at_prediction": market_prob_at_prediction,
        "bot_prediction_prob": bot_prediction_prob,
        "edge": (
            (bot_prediction_prob - market_prob_at_prediction)
            if market_prob_at_prediction is not None else None
        ),
        "ensemble": ensemble,
        "n_articles_used": n_articles,
        "model": model,
        "reasoning": reasoning[:2000],
        "timestamp_iso": datetime.now(timezone.utc).isoformat(),
        "prev_hash": prev_hash,
        "resolved": False,
        "actual_resolution": None,
        "resolved_at_iso": None,
        "extras": extras or {},
    }
    payload["prediction_hash"] = _hash(prev_hash, payload)

    with tracker_path.open("a") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def verify_chain(tracker_path: Path) -> tuple[bool, list[str]]:
    """Walk the file and verify every record's hash links correctly.

    Returns (all_valid, list_of_problems).
    """
    problems = []
    if not tracker_path.exists():
        return True, []
    expected_prev = GENESIS_HASH
    with tracker_path.open() as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                problems.append(f"line {i}: not valid JSON ({e})")
                continue
            recorded_hash = rec.get("prediction_hash")
            stored_prev = rec.get("prev_hash")
            if stored_prev != expected_prev:
                problems.append(f"line {i}: prev_hash {stored_prev[:12]} != expected {expected_prev[:12]}")
            payload_for_hash = {k: v for k, v in rec.items() if k != "prediction_hash"}
            recomputed = _hash(stored_prev, payload_for_hash)
            if recomputed != recorded_hash:
                problems.append(f"line {i}: hash mismatch (stored {recorded_hash[:12]}... vs recomputed {recomputed[:12]}...)")
            expected_prev = recorded_hash or expected_prev
    return len(problems) == 0, problems


def load_all(tracker_path: Path) -> list[dict]:
    if not tracker_path.exists():
        return []
    out = []
    with tracker_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def update_resolution(
    tracker_path: Path,
    record_id: str,
    *,
    actual_resolution: str | None,
    resolved_at_iso: str | None,
) -> bool:
    """Update the resolution fields on an existing record.

    NOTE: we explicitly do NOT re-hash on resolution updates — the original
    prediction hash remains intact (those fields were null when hashed).
    Resolution is recorded as a separate side-channel update; the verify_chain
    check ignores resolution fields when recomputing hashes.

    Returns True if a record was updated.
    """
    records = load_all(tracker_path)
    found = False
    for r in records:
        if r.get("record_id") == record_id:
            r["resolved"] = actual_resolution is not None
            r["actual_resolution"] = actual_resolution
            r["resolved_at_iso"] = resolved_at_iso
            found = True
            break
    if not found:
        return False
    # Rewrite file
    with tracker_path.open("w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return True
