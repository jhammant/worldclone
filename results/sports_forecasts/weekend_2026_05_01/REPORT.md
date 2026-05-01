# Tonight's lineup — accumulator analysis

Bankroll: $100  |  Kelly fraction: 0.25  |  Min edge for accumulator: 2.0pp

## Per-event analysis

| Event | Pick | Bot P | Vegas P (no-vig) | Edge | ML | Decimal | EV/$1 | Quarter-Kelly stake |
|---|---|---|---|---|---|---|---|---|
| Tampa Bay Lightning @ Montreal Canadiens (nhl) | Montreal Canadiens (home) | 55.8% | 48.4% | +7.4pp | -105 | 1.95 | +8.9% | $2.35 |
| Vegas Golden Knights @ Utah Mammoth (nhl) | Vegas Golden Knights (away) | 56.7% | 51.1% | +5.6pp | -115 | 1.87 | +6.0% | $1.73 |
| Liverpool @ Manchester United (epl) | Manchester United (home) | 45.5% | 41.2% | +4.3pp | +130 | 2.30 | +4.6% | $0.89 |
| Buffalo Sabres @ Boston Bruins (nhl) | Boston Bruins (home) | 53.7% | 49.5% | +4.2pp | -110 | 1.91 | +2.5% | $0.69 |
| Los Angeles Lakers @ Houston Rockets (nba) | Los Angeles Lakers (away) | 41.6% | 39.6% | +2.0pp | +142 | 2.42 | +0.7% | $0.12 |
| Fulham @ Arsenal (epl) | Fulham (away) | 12.9% | 11.2% | +1.7pp | +800 | 9.00 | +15.9% | $0.50 |
| Orlando Magic @ Detroit Pistons (nba) | Orlando Magic (away) | 41.6% | 40.9% | +0.7pp | +135 | 2.35 | -2.2% | $0.00 |
| Cleveland Cavaliers @ Toronto Raptors (nba) | Cleveland Cavaliers (away) | 61.1% | 60.9% | +0.2pp | -175 | 1.57 | -4.0% | $0.00 |

## Accumulator candidates

### 3-leg accumulator (top 3 legs by edge)

Legs:
  1. Montreal Canadiens (Tampa Bay Lightning @ Montreal Canadiens) — bot 55.8% vs Vegas 48.4%  edge +7.4pp
  2. Vegas Golden Knights (Vegas Golden Knights @ Utah Mammoth) — bot 56.7% vs Vegas 51.1%  edge +5.6pp
  3. Manchester United (Liverpool @ Manchester United) — bot 45.5% vs Vegas 41.2%  edge +4.3pp

| Metric | Value |
|---|---|
| Combined decimal odds | 8.40x |
| Bot joint P (independence assumption) | 14.40% |
| Vegas joint implied P (no-vig, independence) | 10.20% |
| EV per $1 stake | +20.9% |
| Quarter-Kelly stake (out of $100 bankroll) | $0.70 |

**If all 3 legs hit**: stake $0.70 returns $5.92 (profit $+5.21)

### 4-leg accumulator (top 4 legs by edge)

Legs:
  1. Montreal Canadiens (Tampa Bay Lightning @ Montreal Canadiens) — bot 55.8% vs Vegas 48.4%  edge +7.4pp
  2. Vegas Golden Knights (Vegas Golden Knights @ Utah Mammoth) — bot 56.7% vs Vegas 51.1%  edge +5.6pp
  3. Manchester United (Liverpool @ Manchester United) — bot 45.5% vs Vegas 41.2%  edge +4.3pp
  4. Boston Bruins (Buffalo Sabres @ Boston Bruins) — bot 53.7% vs Vegas 49.5%  edge +4.2pp

| Metric | Value |
|---|---|
| Combined decimal odds | 16.03x |
| Bot joint P (independence assumption) | 7.73% |
| Vegas joint implied P (no-vig, independence) | 5.05% |
| EV per $1 stake | +23.9% |
| Quarter-Kelly stake (out of $100 bankroll) | $0.40 |

**If all 4 legs hit**: stake $0.40 returns $6.37 (profit $+5.97)

### 5-leg accumulator: not enough legs with edge ≥ 2.0pp (4 qualifying)


### Single-bet alternative (every qualifying leg as a straight bet)

| Pick | Stake (¼ Kelly) | If wins, returns | EV/$ | EV ($) |
|---|---|---|---|---|
| Montreal Canadiens (Tampa Bay Lightning @ Montreal Canadiens) | $2.35 | $4.58 | +8.9% | $+0.21 |
| Vegas Golden Knights (Vegas Golden Knights @ Utah Mammoth) | $1.73 | $3.23 | +6.0% | $+0.10 |
| Manchester United (Liverpool @ Manchester United) | $0.89 | $2.06 | +4.6% | $+0.04 |
| Boston Bruins (Buffalo Sabres @ Boston Bruins) | $0.69 | $1.32 | +2.5% | $+0.02 |

**Total**: $5.66 staked across 4 legs → expected profit $+0.37

## Honest caveats

- **Independence assumption is wrong.** Real-world legs correlate (shared news cycle, weather, broadcast slot). Joint P from multiplying singles is an upper bound; correlated risks → fewer "all hit" outcomes than the math suggests.
- **Sample size is N=5.** A favorable EV here is no proof of edge; could easily be variance.
- **Sportsbook accumulator vig compounds.** A real sportsbook would price these worse than the implied joint odds shown.
- **Quarter-Kelly is conservative.** Going full Kelly on parlays is ill-advised when edge confidence is low.
- **Use this as an immutable record + thinking exercise**, not a betting strategy without independent validation.

---

## UK / horse racing addendum

### 2000 Guineas (Newmarket, Sat May 2, 15:35 BST)

3yo colts mile classic. Top of the ante-post market:

| Horse | Best Odds | Implied prob | Notes |
|---|---|---|---|
| Bow Echo | 10/3 (3.33 dec) | 27% | Three career wins; G2 Royal Lodge winner |
| Gstaad | 7/2 (4.5 dec) | 22% | Co-favourite at bet365 |
| Distant Storm | 9/2 (5.5 dec) | 18% | Newmarket form |
| Publish | 9/2 | 18% | bet365 |
| Puerto Rico | 12/1 | 8% | Outsider |

**Bot view: not modelled.** Horse racing is a multi-runner market; the
sports-forecaster pipeline only handles binary/3-way win markets. No edge
calc — listed for completeness as a UK side bet only.

### EPL games — what was forecast

- **Arsenal v Fulham (Sat 17:30)**: Arsenal -250 / draw +500 / Fulham +800.
  Bot P(Arsenal home win) = 76.9% vs Vegas no-vig 74.1% — only +2.8pp edge,
  EV ~+1.5%. Below 2pp threshold for inclusion. The +1.7pp away edge on
  Fulham at +800 is a long-shot lottery — bot 12.9% vs no-vig 11.2%.
  **Pass on both.**

- **Man Utd v Liverpool (Sun 15:30)**: MUN +130 / draw +290 / LIV +175.
  Bot P(MUN home win) = 45.5% vs Vegas no-vig 41.2% → **+4.3pp edge, EV +4.6%
  on the home side**. Included in the 3- and 4-leg accumulators above.
  Caveat: the 3-way market means there's still ~25% chance of a draw which
  is *correctly* priced into the bot's view — this is a true edge call on
  MUN winning outright at home.

