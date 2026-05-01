# LinkedIn post draft (UK punter voice)

Three images to attach in order: `docs/images/weekend_picks.png` first
(the hook), then `docs/images/architecture.png`, then
`docs/images/boxoffice_calibration.png`.

---

## Draft v1 — full version (~290 words)

spent the week building a forecasting toolkit and pointing it at three things: a geopolitical cluster, opening-weekend box office, and this weekend's sports card. running 100% local on an M5 Mac.

the numbers so far:

→ Iran 2026 cluster, 6 questions, post-resolution. Halawi-style LLM forecaster Brier 0.27. Multi-agent monte carlo simulation Brier 0.13. Manifold crowd Brier 0.001. the crowd buried both. the simulation cleared a coin-flip baseline. the LLM forecaster did not.

→ box office, 10 wide releases, ground truth in. MAPE 15.9% vs naive baseline 101%. 80% confidence interval coverage hit 80% — calibrated, not lucky.

→ NBA picks live this week: 4 of 7 hit. one parlay miss because the soccer leg drew (Atlético-Arsenal 1-1) and i hadn't priced the 3-way market properly. that's now fixed.

this weekend's selections are in the repo, timestamped, hash-chained, immutable. four legs, all UK high-street prices, all with the model fancying them over the bookies' no-vig:

• Canadiens to win Game 6 — 10/11 (model 55.8% vs bookies 48.4%)
• Golden Knights to win Game 6 — 5/6 (model 56.7% vs 51.1%)
• Man United to beat Liverpool — 13/10 (model 45.5% vs 41.2%)
• Bruins to win Game 6 — 10/11 (model 53.7% vs 49.5%)

treble at roughly 7/1, theoretical EV +20.9%. 4-fold at 15/1, +23.9%. score-back goes up Monday — won or lost.

stack: Qwen 3.6 27B local via LM Studio (parallel=2 on the M5 128GB), litellm wrapper, exa.ai for date-filtered news, pydantic schemas, around 3,500 lines of python. tests pass on CI.

not betting advice. samples are tiny across all three domains. training-data contamination is real and the mitigations are documented. the Iran simulation beat the LLM forecaster but lost to the crowd — that's the actual result.

repo open: github.com/jhammant/worldclone

---

## Draft v2 — shorter (~190 words)

spent the week building a forecasting toolkit. pointed it at three things — a geopolitical cluster, opening-weekend box office, and this weekend's card. 100% local on an M5 Mac.

results so far:

→ Iran 2026, 6 questions resolved. LLM forecaster Brier 0.27. Multi-agent MC sim 0.13. Manifold crowd 0.001. crowd buried both. sim cleared a coin-flip; the LLM forecaster did not.

→ box office, 10 films, ground truth in. MAPE 15.9% vs 101% naive. 80% CI coverage hit 80% — calibrated.

→ NBA: 4 of 7 picks hit this week.

this weekend's card, all UK high-street prices, model fancies all four:

• Canadiens G6 — 10/11
• Golden Knights G6 — 5/6
• Man Utd v Liverpool — 13/10
• Bruins G6 — 10/11

treble at roughly 7/1, EV +20.9%. 4-fold at 15/1, +23.9%. score-back Monday.

stack: Qwen 3.6 27B local, litellm, exa.ai, pydantic. ~3,500 LOC.

not betting advice. small samples. contamination is real and documented.

github.com/jhammant/worldclone

---

## Notes for iteration

**Voice deliberately**:
- lowercase, direct
- UK punter idiom ("card", "1X2", "treble", "4-fold", "fancies", "the bookies", "model fancy")
- no Americanisms ("parlay" → "treble/4-fold", "moneyline" → "match result", "+EV" stays — universal)
- no emoji, no "thrilled", no "delve", no "lessons learned"

**Optional first-comment** (LinkedIn algorithm rewards engagement on the OP's first reply):
> the immutable tracker is the bit i'm proudest of. SHA-256 chain over each prediction's content + the previous hash. retroactive edits force-rewrite every later line, which shows up as a verification failure. so when i score-back on Monday, you can confirm the picks weren't moved.

**Things to add if you want**:
- Tag a friend / mentor who works in quant or ML
- Link a relevant prior post
- A one-line provocation: "if a 4-fold treble at 15/1 with documented +EV doesn't move you, what does"

**Things to drop if length matters**:
- The stack para (engineers will find it in the repo)
- The Iran result if you don't want geopolitics on your feed (but it's the strongest "the toolkit is honest about losing" data point)

## Monday score-back template

> monday score-back. weekend card was [list]. results: [hit/miss per leg]. treble: [hit/miss], 4-fold: [hit/miss]. running record: [n/m] picks, Brier [x]. P&L if you'd dollar-staked the singles: [£]. next card goes up [day].
> 
> the [winning leg] was the model's biggest fancy and it [hit/missed]. [interesting leg] is the one i'd flag for follow-up.
> 
> repo updated: github.com/jhammant/worldclone
