# Weekend Card — 1–3 May 2026

Bank: £100  ·  Stake plan: quarter-Kelly  ·  Minimum edge: 2pp over the
market price.

Prices below are the **best** I could find around the UK high-street
boards (Bet365, Sky Bet, Ladbrokes, William Hill, Coral, Paddy Power).
The model says the bookies are short on these four selections.

## Where the value is

| Selection | Market | Best UK price | Decimal | Model fancy | Bookie no-vig | Edge |
|---|---|---|---|---|---|---|
| **Montreal Canadiens** to win Game 6 vs Tampa Bay | NHL Match Result | **10/11** | 1.95 | 55.8% | 48.4% | **+7.4pp** |
| **Vegas Golden Knights** to win Game 6 at Utah | NHL Match Result | **5/6** | 1.87 | 56.7% | 51.1% | **+5.6pp** |
| **Manchester United** to beat Liverpool | EPL 90-min 1X2 | **13/10** | 2.30 | 45.5% | 41.2% | **+4.3pp** |
| **Boston Bruins** to beat Buffalo Game 6 | NHL Match Result | **10/11** | 1.91 | 53.7% | 49.5% | +4.2pp |

"Bookie no-vig" is the implied price after stripping the overround. The
edge is what the model says you're getting over a fair-game price.

The Canadiens line is the value pick of the weekend on these numbers
(+7.4pp). All four are ranked by edge, all four clear the 2pp filter.

## What I'm actually putting on

### Singles (the boring honest version)

| Selection | Stake (¼ Kelly off £100) | Returns if it wins |
|---|---|---|
| Canadiens to win G6 — 10/11 | £2.35 | £4.58 |
| Golden Knights to win G6 — 5/6 | £1.73 | £3.23 |
| Man United to win — 13/10 | £0.89 | £2.06 |
| Bruins to win G6 — 10/11 | £0.69 | £1.32 |
| **Total** | **£5.66** | EV +£0.37 |

### Trebles + 4-folds (the interesting maths)

**Treble**: Canadiens + Golden Knights + Man United at combined **8.40**
(roughly 7/1).

| Stake | Combined price | Returns | Bot joint prob | Bookie joint | Theoretical EV |
|---|---|---|---|---|---|
| £0.70 (¼ Kelly) | 8.40 | £5.92 | 14.40% | 10.20% | **+20.9%** |

**4-fold**: add the Bruins (which is already odds-on at 10/11) and the
combined price runs to **16.03**, around 15/1.

| Stake | Combined price | Returns | Bot joint prob | Bookie joint | Theoretical EV |
|---|---|---|---|---|---|
| £0.40 (¼ Kelly) | 16.03 | £6.37 | 7.73% | 5.05% | **+23.9%** |

The 4-fold has the bigger headline EV but the maths assumes the legs are
independent — three NHL Game 6 outcomes are not (favourite-bias news
cycle, ref tightness in elimination games, broadcast schedule). So
discount the joint probability ~15–25% in your head before you fancy it.

## What I'm passing on

- **Magic at Detroit (NBA G6) — Pistons 8/11**: model says 41% home win,
  bookie no-vig 41%. No edge, walk away.
- **Cavs at Toronto (NBA G6) — Cavs 4/7 odds-on**: model and bookie
  agree at 61%. Skinny price for nothing in return.
- **Arsenal v Fulham — Gunners 2/7 odds-on**: ~77% chance, model has it
  at 77% too. UCL second-leg congestion makes the price short. Pass.
- **76ers at Celtics G7 — Celtics 1/4**: forecaster wouldn't even spit a
  number out (the LLM ranking step kept failing on length). Bookies have
  Boston at -310, around 76% — too short to fade without a strong view.
  Stay away.

## Speciality and UK side bets (not in the accumulator)

**2,000 Guineas, Newmarket — Saturday 15:35**

3yo colts mile classic. Top of the antepost market with the high-street:

| Horse | Best Odds | Implied prob | Notes |
|---|---|---|---|
| Bow Echo | 10/3 | 27% | Group 2 Royal Lodge winner, three career wins |
| Gstaad | 7/2 | 22% | Bet365 co-fav |
| Distant Storm | 9/2 | 18% | Newmarket form |
| Publish | 9/2 | 18% | bet365 |
| Puerto Rico | 12/1 | 8% | Outsider |

The model doesn't price multi-runner racing markets — listed for
completeness only. Each-way punters typically take 1/5 the odds first
four on a big classic.

## How the bookies' overround stacks up

The overround is the bookies' built-in margin. For a 2-way market it's
`P(home) + P(away) - 100%`. Anything over 0% is the punter paying for
the privilege of having a market open.

| Market | Bookie home | Bookie away | Overround |
|---|---|---|---|
| MTL G6 (Canadiens) | -105 / 1.95 | TBL -120 / 1.83 | 5.94% |
| VGK G6 (Mammoth h) | -105 / 1.95 | VGK -115 / 1.87 | 4.89% |
| BOS G6 (Bruins h) | -110 / 1.91 | BUF -115 / 1.87 | 5.83% |
| Man Utd v LIV (3-way) | 13/10 + draw 26/9 + 19/10 | — | 4.32% |

Hockey is priced tighter than you'd think on the high street — sub-6%
margin is where serious arb hunters operate. Football is wider but
nothing crazy.

## Honest caveats

- **This is not betting advice.** It is an immutable record of what the
  model said before the games. Score-back goes up Monday.
- **Sample size is tiny.** 4 selections. A 2/4 or 3/4 weekend is well
  inside variance even on +EV bets. A 0/4 doesn't disprove the model.
  Multi-week tracking needed.
- **Bookies will boost the parlay vig.** Ladbrokes / Bet365 etc. will
  price these "trebles" worse than the implied joint of the singles —
  the +20.9% / +23.9% theoretical EV is an upper bound; real bookmaker
  treble vig adds 2–4% to the overround per leg.
- **Independence is wrong on hockey nights.** Three Game 6s in the same
  evening share narrative — favourite-bias, broadcast slot, referee
  tightness in elimination games.
- **Quarter-Kelly is conservative on purpose.** Full Kelly on a model
  with N=4 of historical evidence is daft.
- **Only bet what you can afford to lose.** Use Gamcare /
  BeGambleAware if betting stops being recreational.

## How this was produced

- Forecaster pipeline: `worldclone/sports/pipeline.py`. 5-variant
  ensemble (form_and_stats, vegas_anchored, playoff_dynamics,
  devils_advocate, naive) at temperature 0.7, on local Qwen 3.6 27B via
  LM Studio (parallel=2 on M5 Mac).
- News retrieval: Exa.ai with `endPublishedDate=2026-05-01`. Defensive
  post-filter drops dateless articles (cuts down on
  retraining-data leaks).
- Accumulator pricing: `scripts/accumulator_analysis.py`. Kelly
  criterion with quarter-Kelly haircut.
- Tracker: SHA-256 Merkle chain in `worldclone/tracker/store.py` so
  you can verify these picks weren't moved after the fact.
- Repository: github.com/jhammant/worldclone (MIT, public).
