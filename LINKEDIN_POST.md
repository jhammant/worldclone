# LinkedIn post draft

This is a starting draft to copy-paste into LinkedIn. Iterate freely —
voice should sound like you, not a writeup. Three images attach: 
`docs/images/architecture.png`, `docs/images/boxoffice_calibration.png`,
`docs/images/weekend_picks.png`.

---

## Draft v1 (results-first, ~280 words)

spent the week building a forecasting toolkit and pointing it at three things: a geopolitical cluster, opening-weekend box office, and this weekend's sports slate. running 100% local on an M5 Mac.

the numbers so far:

→ Iran 2026 cluster, 6 questions, post-resolution. Halawi-style LLM forecaster Brier 0.27. Multi-agent monte carlo simulation Brier 0.13. Manifold crowd Brier 0.001. the crowd buried both. the simulation cleared naive 50%. the LLM forecaster did not.

→ box office, 10 wide releases, ground truth landed. MAPE 15.9% vs naive baseline 101%. 80% CI coverage hit 80% — calibrated, not lucky.

→ NBA picks live this week: 4 of 7 hit. one parlay miss because i didn't model the 3-way market on a soccer leg (Atlético-Arsenal drew). that's now fixed.

this weekend's picks are in the repo, timestamped, hash-chained, and immutable. four legs:

• Canadiens home (NHL G6, +7.4 pp edge)
• Golden Knights road (NHL G6, +5.6 pp edge)
• Man Utd home (EPL, +4.3 pp edge)
• Bruins home (NHL G6, +4.2 pp edge)

3-leg parlay at +20.9% theoretical EV. 4-leg at +23.9%. score-back coming Monday — good or bad.

stack: Qwen 3.6 27B local via LM Studio (parallel=2 on the M5 128GB), litellm wrapper, exa.ai for date-filtered news, pydantic schemas, around 3,500 lines of python. tests pass on CI.

none of this is betting advice. samples are tiny across all three domains. training-data contamination is real and the mitigations are documented (date-filtered retrieval, notes scrubber, post-cutoff cutoffs). the Iran simulation beat the LLM forecaster but lost to the crowd — that's the actual result.

repo open: github.com/jhammant/worldclone

---

## Notes for iteration

**Keep**: numbers in the first 3 lines, the "the crowd buried both. the simulation cleared naive 50%. the LLM forecaster did not." line, the Monday score-back commitment.

**Maybe trim**: the stack para if length matters; the bullet list if you want a cleaner flow.

**Things to deliberately avoid**:
- emoji
- "I'm thrilled to share" / "excited to announce"
- "as we move into the future of AI"
- "lessons learned" framing
- any employer mention

**Image upload order**:
1. `weekend_picks.png` first (the hook)
2. `architecture.png` second (the engineer-bait)
3. `boxoffice_calibration.png` third (proof the methodology calibrates)

**Optional first-comment** (LinkedIn algorithm rewards engagement on the OP's first reply):
> the immutable tracker is the bit i'm proudest of. SHA-256 chain over each prediction's content + the previous hash. retroactive edits force-rewrite every later line, which shows up as a verification failure. so when i score-back on Monday, you can confirm the picks weren't moved.

## Draft v2 — shorter (~180 words, single screen)

Use this if the longer version feels overstuffed.

spent the week building a forecasting toolkit. pointed it at three things — a geopolitical cluster, opening-weekend box office, and this weekend's sports slate. 100% local on an M5 Mac.

results so far:

→ Iran 2026, 6 questions, resolved. LLM forecaster Brier 0.27. Multi-agent MC sim Brier 0.13. Manifold crowd 0.001. crowd buried both. sim cleared naive 50%; the LLM forecaster did not.

→ box office, 10 films, ground truth in. MAPE 15.9% vs 101% naive. 80% CI coverage hit 80% — calibrated.

→ NBA: 4 of 7 picks hit this week.

weekend picks are in the repo, timestamped and hash-chained. MTL home, VGK road, MUN home, BOS home. 3-leg parlay +20.9% theoretical EV. score-back Monday.

stack: Qwen 3.6 27B local, litellm, exa.ai, pydantic. ~3,500 LOC.

not betting advice. small samples. contamination is real and documented.

github.com/jhammant/worldclone

---

## What goes in the Monday follow-up post

Template, fill in actuals:

> monday score-back. weekend picks were [list]. results: [hit/miss per leg]. parlay: [hit/miss]. running record after one week: [n/m] picks, Brier [x]. running P&L if you'd dollar-staked the singles: [$]. next batch goes up [day].
> 
> the [winning leg] was the bot's biggest edge call and it [hit/missed]. the [interesting leg] is the one i'd flag for follow-up.
> 
> repo updated with results: github.com/jhammant/worldclone
