"""Classify Manifold pool into Subset A/B/C for the simulation-vs-forecaster bake-off.

Subset A — narrow factual / numerical thresholds. Tested by forecaster only.
Subset B — actor-driven scenarios with named entities making decisions. Both methods.
Subset C — junk/personal/ambiguous. Excluded.

Heuristic classifier — keyword-based, not ML. Output is a starting candidate
set for human review, not a final dataset.
"""
import json, re, datetime, sys
from collections import Counter

POOL = "data/manifold_pool_raw.json"
OUT_DIR = "data"

# Subset B signals: named geopolitical actors + verbs of decision/action
ACTOR_KEYWORDS = [
    # Heads of state / political figures
    "trump","biden","harris","putin","xi","modi","macron","starmer","netanyahu",
    "orban","erdogan","zelensky","khamenei","kim jong","sunak","meloni","milei",
    # Bodies / entities with agency
    "congress","senate","house","scotus","supreme court","white house","kremlin",
    "nato","un security","european union","fed","federal reserve","ecb","opec",
    # Countries acting (paired with action verbs filtered below)
    "us ","u.s. ","usa","russia","china","iran","israel","ukraine","north korea",
    "hungary","taiwan","gaza","hamas","hezbollah","houthi",
]
ACTION_VERBS = [
    "invade","attack","strike","shoot down","sanction","negotiate","sign","veto",
    "announce","resign","step down","be elected","win the election","lose the election",
    "remain","be removed","be impeached","ratify","withdraw","deploy","ceasefire",
    "boots on the ground","nuke","arrest","indict","pardon","deport","ban","seize",
    "be released","be charged","convict","acquit","pass","reject","approve","veto",
]

# Subset A signals: numerical / market / threshold language with no actor decision
NARROW_KEYWORDS = [
    "stock","price","close above","close below","reach $","exceed","below $",
    "btc","bitcoin","eth","spy","nvda","intc","aapl","s&p","ftse","wti",
    "gdp","cpi","inflation","unemployment rate","yield",
    "release","launch","ship","ipo","earnings","beat consensus",
    "score","goals","points","championship","world cup","super bowl","nba","nhl","ufc",
    "sumo","tournament","playoffs","final","semifinal",
    "temperature","hurricane","earthquake","storm",
]

# Subset C signals: personal/ambiguous — exclude
JUNK_KEYWORDS = [
    "manifold ","mana ","my friend","my dad","my mom","my cat","my dog","my wife",
    "my husband","my partner","my boss","my kid","i will","i'll","will i ",
    "[short fuse]","short fuse","acx 2026","putnam","spelling","number sense",
    "easter dinner","poll","forecasting tournament",
]


def classify(q: str) -> str:
    ql = q.lower()
    if any(j in ql for j in JUNK_KEYWORDS):
        return "C"
    has_actor = any(k in ql for k in ACTOR_KEYWORDS)
    has_action = any(v in ql for v in ACTION_VERBS)
    has_narrow = any(n in ql for n in NARROW_KEYWORDS)

    # Sports / markets / numerical thresholds → A
    if has_narrow and not (has_actor and has_action):
        return "A"
    # Actor + decision verb → B
    if has_actor and has_action:
        return "B"
    # Actor without action verb (e.g. "Will Putin still be president?") → B
    if has_actor:
        return "B"
    return "C"


def main():
    with open(POOL) as f:
        markets = json.load(f)

    counts = Counter()
    bucketed = {"A": [], "B": [], "C": []}
    for m in markets:
        bucket = classify(m["question"])
        counts[bucket] += 1
        m_slim = {
            "id": m["id"],
            "question": m["question"],
            "url": m.get("url",""),
            "resolution": m.get("resolution"),
            "resolutionProbability": m.get("resolutionProbability"),
            "resolutionTime": m.get("resolutionTime"),
            "createdTime": m.get("createdTime"),
            "closeTime": m.get("closeTime"),
            "volume": m.get("volume"),
            "uniqueBettorCount": m.get("uniqueBettorCount"),
            "creatorUsername": m.get("creatorUsername"),
            "bucket": bucket,
        }
        bucketed[bucket].append(m_slim)

    print(f"Total: {len(markets)}")
    for b in ("A","B","C"):
        print(f"  Subset {b}: {counts[b]}")

    # Sort each by volume desc
    for b in bucketed:
        bucketed[b].sort(key=lambda m: m.get("volume",0), reverse=True)

    with open(f"{OUT_DIR}/subset_A_narrow.json","w") as f:
        json.dump(bucketed["A"], f, indent=2)
    with open(f"{OUT_DIR}/subset_B_actors.json","w") as f:
        json.dump(bucketed["B"], f, indent=2)
    with open(f"{OUT_DIR}/subset_C_excluded.json","w") as f:
        json.dump(bucketed["C"], f, indent=2)

    print("\nSubset B (actor-driven, top 25 by volume) — the head-to-head test set:")
    for m in bucketed["B"][:25]:
        rd = datetime.datetime.fromtimestamp(m["resolutionTime"]/1000).date()
        print(f"  [{rd}] [{m.get('resolution','?'):>4}] v={m['volume']:>7.0f} {m['question'][:95]}")

    print("\nSubset A (narrow/numerical, top 10 by volume) — forecaster-only test set:")
    for m in bucketed["A"][:10]:
        rd = datetime.datetime.fromtimestamp(m["resolutionTime"]/1000).date()
        print(f"  [{rd}] [{m.get('resolution','?'):>4}] v={m['volume']:>7.0f} {m['question'][:95]}")


if __name__ == "__main__":
    main()
