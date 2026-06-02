# CLAUDE.md — value betting bot

Automated **value betting** bot: estimate a fair probability from the market's
own numbers, bet the Betfair Exchange price when it beats fair (after
commission), as close to kickoff as possible, log taken value + CLV, and bet at
most one event once. Evidence base: Kaunitz et al. "Beating the bookies with
their own numbers" + a practitioner running it on Betfair.

## Run it
```bash
python run.py go --budget 1000 --stake 50     # set budget/stake, start betting
python run.py backtest --data "*.csv" --sweep  # validate + tune on real history
python run.py validate      # is the edge real? go/no-go on captured CLV (see DRYRUN.md)
python run.py doctor        # preflight checks before going live
python run.py status        # bankroll / exposure / risk / CLV dashboard
python -m unittest discover -s tests   # pure-stdlib, offline
```
Runs fully offline in **sample + paper** mode with **no third-party deps**.
Live needs `requests`, `PyYAML`, `betfairlightweight` (see requirements.txt) and
`.env` keys (`ODDS_API_KEY`, `BETFAIR_*`).

## Architecture (data flow)
```
truth model (pinnacle | weighted consensus | kaunitz | blend)  ─┐
                                                                 ├─ EventMatcher ─ ValueDetector ─ Bankroll ─ Risk ─ Executor ─ Store
Betfair Exchange prices ─────────────────────────────────────── ┘   (alias/      (+EV net of   (Kelly/   (breakers) (paper|     (SQLite+CSV,
                                                                      ambiguity)    commission,   flat,                betfair)    CLV, settle)
                                                                                    +CLV only)    liquidity)
```

## Module map (`bot/`)
- `config.py` — layered config (defaults < yaml < env) + `validate()`.
- `models.py` — dataclasses: Outcome/BookOdds/MarketBoard, FairLine, VenueQuote,
  ValueBet (taken value + exp_clv + exchange ids), PlacementResult.
- `devig.py` — multiplicative/additive/shin/power/**ensemble** de-vig.
- `pinnacle.py` — Pinnacle truth (direct API + via The Odds API).
- `consensus.py` — weighted (Power-Method, recency-weighted) + Kaunitz consensus.
- `aliases.py` — team-name normalisation + alias map + similarity.
- `matcher.py` — strict, alias-aware, ambiguity-rejecting event matching.
- `value.py` — ValueDetector (commission, edge haircut, liquidity, overround,
  expected-CLV filter, one-bet-per-event) + Kelly/EV.
- `bankroll.py` — Kelly or flat staking + caps (incl. liquidity cap).
- `risk.py` — circuit breakers + per-bet stake caps (daily/exposure).
- `betfair_client.py` — one Betfair session: prices, placement, cancel,
  cleared-orders, keep-alive, price-ladder rounding.
- `execution/` — paper (default) + betfair executor.
- `scheduler.py` — continuous near-kickoff runner: adaptive polling, dedup,
  CLV capture (model + market close), auto-settle, line-move guard.
- `store.py` — SQLite/CSV; settlement (manual + from Betfair), CLV, P&L, meta.
- `backtest.py` — football-data.co.uk loader, run_backtest, edge buckets, sweep.
- `http.py` — retrying HTTP with backoff.
- `bot.py` — orchestration + live-money safety gate.
- `run.py` — CLI: go | scan | run | watch | backtest | doctor | status | report | settle.

## Key invariants / safety
- **Never bets real money** unless `live: true` AND `executor: betfair` AND
  creds present; everything else falls back to the paper executor.
- **At most one bet per event** (detector keeps best edge; store dedups across runs).
- **Only +expected-CLV bets** (taken price beats fair gross of commission).
- **Circuit breakers** can halt all betting; stakes capped to daily/exposure/liquidity.
- Edits must keep `python -m unittest discover -s tests` green (offline, stdlib).

## Honest status
The strategy is evidence-based and the implementation is faithful and well
tested, but **profitability is not guaranteed**: edges are thin, variance is
large, markets are efficient, and the Betfair live path (placement/settlement)
is structurally complete but unvalidated against the real API. The go/no-go
signal is **positive CLV vs the market close over a few hundred (dry-run or real)
bets** — see `report` / `status`. Always validate via `backtest` first.
