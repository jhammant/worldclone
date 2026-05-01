"""Build data/iran_cluster.json from subset_B_actors.json + hand-curated criteria.

Hand-curated content reflects the Iran-context research conducted during planning.
Resolution criteria are paraphrased from the actual Manifold market descriptions.
"""
from __future__ import annotations

import json
from pathlib import Path

# Hand-curated criteria + questionnaire shape.
# Keys MUST match the IDs in data/subset_B_actors.json.
IRAN_QUESTIONS = {
    "56EZq5c6QS": {
        "questionnaire_key": "us_ground_troops_iran_2026",
        "questionnaire_prompt": (
            "By the end of 2026, did US uniformed armed forces enter Iranian sovereign "
            "territory under US government orders for any military mission "
            "(including SAR/raids/limited ops)? Mercenaries and contractors do NOT count "
            "unless under US government orders. Accidental border crossings do NOT count."
        ),
        "resolution_criteria": (
            "YES if US ground troops physically entered Iranian soil for a military mission. "
            "Rescue teams count if rescuers exit aircraft onto Iranian soil. Mercenaries and "
            "contractors only count under US gov't orders. Accidental border crossings do NOT count."
        ),
    },
    "ZctCIAhQsu": {
        "questionnaire_key": "iran_shoots_down_us_aircraft_by_mar31",
        "questionnaire_prompt": (
            "By March 31 2026, did Iran shoot down a manned US military plane or helicopter? "
            "Damaged-and-emergency-landed aircraft do NOT count. The aircraft must be brought down."
        ),
        "resolution_criteria": (
            "YES if Iran shot down a manned US military aircraft by March 31 2026 per trusted "
            "news sources. F-35 emergency landing on March 19 (damaged but intact) does NOT count. "
            "F-15E shootdown on April 3 was AFTER cutoff and does NOT count."
        ),
    },
    "8tLLpnUuzz": {
        "questionnaire_key": "trump_boots_on_ground_iran_by_jul4_2026",
        "questionnaire_prompt": (
            "Before July 4 2026, did uniformed US armed forces members physically enter "
            "Iran's sovereign land to conduct a military mission? CIA, contractors, or "
            "mercenaries do NOT count unless under US government orders."
        ),
        "resolution_criteria": (
            "YES if uniformed US Armed Forces members physically entered Iran for a military "
            "mission before July 4 2026. SAR, raids, limited ops all count. Covert ops count "
            "only if officially acknowledged or confirmed by 2+ major outlets."
        ),
    },
    "SuSt8qdg6E": {
        "questionnaire_key": "iran_kills_5plus_us_soldiers_by_mar31",
        "questionnaire_prompt": (
            "Between roughly March 6 and March 31 2026, did Iran kill 5 or more additional "
            "US service members (i.e. additional to the 6 already killed by March 5)? "
            "Total threshold for YES is 11+ US service members killed by Iranian attacks by March 31."
        ),
        "resolution_criteria": (
            "YES if 6+ ADDITIONAL US service members killed by Iranian attacks by March 31 2026 "
            "(total ≥ 11). Based on official DoD/CENTCOM death counts."
        ),
    },
    "z0Lq2ONdgq": {
        "questionnaire_key": "trump_nukes_iran_by_apr10",
        "questionnaire_prompt": (
            "Before 8pm EST on April 10 2026, did the United States under President Trump "
            "use a nuclear weapon against Iran?"
        ),
        "resolution_criteria": (
            "YES if literal nuclear weapon used by Trump against Iran before April 10 2026 8pm EST."
        ),
    },
    "c88qSPCyLl": {
        "questionnaire_key": "trump_strikes_iran_infrastructure_by_apr12",
        "questionnaire_prompt": (
            "Before April 12 2026 23:59 UTC, did the US military directly strike Iranian "
            "civilian-relevant infrastructure (oil refineries, power grids, nuclear facilities, "
            "or transport infrastructure)? Strikes on military sites do NOT count. "
            "Third-party (Israel, insurgent) strikes without direct US involvement do NOT count."
        ),
        "resolution_criteria": (
            "YES only if direct US military strike on Iranian infrastructure (oil refineries, "
            "power grids, nuclear, transport) by April 12 2026 23:59 UTC. Strikes on military "
            "sites do NOT count. Third-party actions without direct US involvement do NOT count."
        ),
    },
    # 7th market: "Will there be a Assassination attempt on Donald Trumps life before the the midterms"
    # Excluded — domestic, not Iran cluster, weakly correlated. Keeping pilot tightly scoped.
}


def main() -> None:
    src = Path("data/subset_B_actors.json")
    with src.open() as f:
        all_b = json.load(f)
    all_b_by_id = {m["id"]: m for m in all_b}

    out = []
    missing = []
    for mid, ann in IRAN_QUESTIONS.items():
        m = all_b_by_id.get(mid)
        if m is None:
            missing.append(mid)
            continue
        out.append({
            "id": mid,
            "question": m["question"],
            "url": m["url"],
            "resolution": m.get("resolution"),
            "resolution_probability": m.get("resolutionProbability"),
            "resolution_time_ms": m.get("resolutionTime"),
            "close_time_ms": m.get("closeTime"),
            "create_time_ms": m.get("createdTime"),
            "volume": m.get("volume", 0.0),
            "unique_bettors": m.get("uniqueBettorCount", 0),
            "resolution_criteria": ann["resolution_criteria"],
            "questionnaire_key": ann["questionnaire_key"],
            "questionnaire_prompt": ann["questionnaire_prompt"],
        })

    if missing:
        print(f"WARN: {len(missing)} IDs not found in subset_B_actors.json: {missing}")

    dst = Path("data/iran_cluster.json")
    with dst.open("w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {len(out)} questions → {dst}")
    for q in out:
        res = q.get("resolution") or "?"
        print(f"  [{res:>4}] {q['question'][:80]}")


if __name__ == "__main__":
    main()
