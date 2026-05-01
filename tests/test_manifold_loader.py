"""Sanity-check the curated Iran cluster file."""
from __future__ import annotations

from pathlib import Path

import pytest

from worldclone.common.io import ManifoldQuestion
from worldclone.common.manifold import load_iran_cluster


def test_iran_cluster_loads():
    path = Path("data/iran_cluster.json")
    assert path.exists(), f"Run scripts/build_iran_cluster.py first (no {path})"
    qs = load_iran_cluster(path)
    assert len(qs) >= 5, f"expected at least 5 questions, got {len(qs)}"


def test_all_questions_have_resolution():
    qs = load_iran_cluster()
    for q in qs:
        assert q.resolution in ("YES", "NO"), f"{q.id} has unscoreable resolution: {q.resolution}"


def test_all_questions_have_questionnaire_fields():
    qs = load_iran_cluster()
    for q in qs:
        assert q.questionnaire_key, f"{q.id} missing questionnaire_key"
        assert q.questionnaire_prompt, f"{q.id} missing questionnaire_prompt"
        assert q.resolution_criteria, f"{q.id} missing resolution_criteria"


def test_questionnaire_keys_unique():
    qs = load_iran_cluster()
    keys = [q.questionnaire_key for q in qs]
    assert len(keys) == len(set(keys)), f"duplicate keys: {keys}"


def test_resolution_binary_property():
    qs = load_iran_cluster()
    for q in qs:
        rb = q.resolution_binary
        assert rb in (0, 1), f"{q.id} resolution_binary not in 0/1: {rb}"


def test_at_least_one_yes_and_one_no():
    """A pilot dominated by one outcome has weak signal — confirm we have spread."""
    qs = load_iran_cluster()
    yes = sum(1 for q in qs if q.resolution == "YES")
    no = sum(1 for q in qs if q.resolution == "NO")
    assert yes >= 1, "no YES outcomes — pilot will have weak signal"
    assert no >= 1, "no NO outcomes — pilot will have weak signal"


def test_close_probabilities_in_range():
    qs = load_iran_cluster()
    for q in qs:
        if q.resolution_probability is not None:
            assert 0 <= q.resolution_probability <= 1, f"{q.id}: prob={q.resolution_probability}"


def test_pydantic_validates_invalid_resolution():
    with pytest.raises(ValueError):
        ManifoldQuestion(
            id="x", question="q", url="", resolution="MAYBE",
            close_time_ms=0, create_time_ms=0,
        )
