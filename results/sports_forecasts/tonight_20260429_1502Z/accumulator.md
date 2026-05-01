# Tonight's lineup — accumulator analysis

Bankroll: $100  |  Kelly fraction: 0.25  |  Min edge for accumulator: 2.0pp

## Per-event analysis

| Event | Pick | Bot P | Vegas P (no-vig) | Edge | ML | Decimal | EV/$1 | Quarter-Kelly stake |
|---|---|---|---|---|---|---|---|---|
| Arsenal FC @ Atlético Madrid (ncaaf) | Arsenal FC (away) | 63.0% | 55.0% | +8.0pp | +145 | 2.45 | +54.4% | $9.37 |
| Houston Rockets @ Los Angeles Lakers (nba) | Houston Rockets (away) | 44.8% | 38.4% | +6.4pp | +150 | 2.50 | +12.0% | $2.00 |
| Los Angeles Kings @ Colorado Avalanche (nhl) | Colorado Avalanche (home) | 63.6% | 58.0% | +5.6pp | -150 | 1.67 | +6.0% | $2.25 |
| Montreal Canadiens @ Tampa Bay Lightning (nhl) | Tampa Bay Lightning (home) | 61.5% | 59.6% | +1.9pp | -160 | 1.62 | -0.1% | $0.00 |
| Toronto Raptors @ Cleveland Cavaliers (nba) | Cleveland Cavaliers (home) | 76.4% | 76.0% | +0.4pp | -380 | 1.26 | -3.5% | $0.00 |

## Accumulator candidates

### 3-leg accumulator (top 3 legs by edge)

Legs:
  1. Arsenal FC (Arsenal FC @ Atlético Madrid) — bot 63.0% vs Vegas 55.0%  edge +8.0pp
  2. Houston Rockets (Houston Rockets @ Los Angeles Lakers) — bot 44.8% vs Vegas 38.4%  edge +6.4pp
  3. Colorado Avalanche (Los Angeles Kings @ Colorado Avalanche) — bot 63.6% vs Vegas 58.0%  edge +5.6pp

| Metric | Value |
|---|---|
| Combined decimal odds | 10.21x |
| Bot joint P (independence assumption) | 17.95% |
| Vegas joint implied P (no-vig, independence) | 12.24% |
| EV per $1 stake | +83.2% |
| Quarter-Kelly stake (out of $100 bankroll) | $2.26 |

**If all 3 legs hit**: stake $2.26 returns $23.07 (profit $+20.81)

### 4-leg accumulator: not enough legs with edge ≥ 2.0pp (3 qualifying)


### 5-leg accumulator: not enough legs with edge ≥ 2.0pp (3 qualifying)


### Single-bet alternative (every qualifying leg as a straight bet)

| Pick | Stake (¼ Kelly) | If wins, returns | EV/$ | EV ($) |
|---|---|---|---|---|
| Arsenal FC (Arsenal FC @ Atlético Madrid) | $9.37 | $22.96 | +54.4% | $+5.09 |
| Houston Rockets (Houston Rockets @ Los Angeles Lakers) | $2.00 | $5.00 | +12.0% | $+0.24 |
| Colorado Avalanche (Los Angeles Kings @ Colorado Avalanche) | $2.25 | $3.75 | +6.0% | $+0.13 |

**Total**: $13.62 staked across 3 legs → expected profit $+5.47

## Honest caveats

- **Independence assumption is wrong.** Real-world legs correlate (shared news cycle, weather, broadcast slot). Joint P from multiplying singles is an upper bound; correlated risks → fewer "all hit" outcomes than the math suggests.
- **Sample size is N=5.** A favorable EV here is no proof of edge; could easily be variance.
- **Sportsbook accumulator vig compounds.** A real sportsbook would price these worse than the implied joint odds shown.
- **Quarter-Kelly is conservative.** Going full Kelly on parlays is ill-advised when edge confidence is low.
- **Use this as an immutable record + thinking exercise**, not a betting strategy without independent validation.
