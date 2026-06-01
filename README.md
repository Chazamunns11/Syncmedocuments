# Value Betting Bot

A sports betting bot that **identifies** profitable value bets, **places** them,
and **logs** every one — with realistic safety rails.

It works by estimating a *fair* probability for each outcome (de-vigging a sharp
reference bookmaker such as Pinnacle), then betting wherever another book offers
odds that beat that fair price by a configurable margin (+EV). Stakes are sized
with fractional Kelly, placed through a pluggable executor, and recorded to a
database with full P&L tracking.

> It runs out of the box on **offline sample data** in **paper (simulated) mode**
> with **zero third-party dependencies** — try it before wiring up any account.

---

## ⚠️ Read this first — the realities of "auto-placing" bets

1. **Traditional sportsbooks (bet365, William Hill, DraftKings, …) do not offer a
   public API to place bets, and their Terms of Service ban automated betting.**
   Value/arb bettors routinely get stake-limited or have accounts closed. There
   is no sanctioned way to auto-place into them.
2. **The legitimately automatable venue is a betting *exchange*.** This bot ships
   a real **Betfair Exchange** executor — Betfair publishes an official API and
   permits automated placement under its developer programme. (Smarkets is a
   similar option you could add.)
3. **You are responsible** for gambling laws in your jurisdiction, the terms of
   any account you use, taxes, and your own losses. Positive *expected* value
   does not mean you can't lose — variance is real and bankrolls go bust if
   over-staked. This software is provided for educational use, with no warranty.
   Only ever risk money you can afford to lose, and use the responsible-gambling
   tools your operator provides.

The bot **cannot place a real bet unless you explicitly opt in** (`live: true`
*and* `executor: betfair` *and* real credentials). Everything else is paper.

---

## Quick start

```bash
# 1. (optional) create a venv and install live-mode deps
pip install -r requirements.txt        # not needed for offline/paper demo

# 2. identify value bets from offline sample data
python run.py scan

# 3. identify, place (paper) and log
python run.py run

# 4. see logged bets and running P&L
python run.py report

# 5. settle a finished bet (use the ref printed by `run`/`report`)
python run.py settle --ref paper-xxxxxxxx --result WON
```

## How it works

```
 providers ──▶ ValueDetector ──▶ BankrollManager ──▶ Executor ──▶ BetStore
  (odds)        (+EV bets)         (Kelly stakes)     (place)      (log + P&L)
```

| Stage | Module | What it does |
|-------|--------|--------------|
| Fetch | `bot/providers/` | Normalise odds into `MarketBoard`s. `sample` (offline) or `the_odds_api` (live). |
| Identify | `bot/value.py` + `bot/devig.py` | De-vig the sharp book → fair prob; flag outcomes where another book's price beats fair by ≥ `min_edge`. Computes EV + Kelly. |
| Size | `bot/bankroll.py` | Fractional-Kelly stake with per-bet, min/max and total-exposure caps. |
| Place | `bot/execution/` | `PaperExecutor` (default, simulated) or `BetfairExecutor` (real exchange). |
| Log | `bot/store.py` | SQLite + CSV of every identified and placed bet; `settle()` records realised P&L/ROI. |

### De-vig methods
`multiplicative` (default), `additive`, and `shin` (favourite–longshot aware).
See `bot/devig.py`. Pick via `devig_method` in config.

### Why a "sharp" reference book?
Sharp books (Pinnacle) price close to true probability and accept big bets, so
their de-vigged line is the cheapest good estimate of "truth". The detector
compares soft-book prices against it. If the reference book is missing for a
market, it falls back to the de-vigged consensus of all books.

## Going live (real money, Betfair)

1. Open and fund a Betfair account; get an **Application Key** at
   <https://developer.betfair.com> and (recommended) set up certificate login.
2. `cp .env.example .env` and fill in `BETFAIR_*` (and `ODDS_API_KEY`).
   Load it: `set -a; . ./.env; set +a`.
3. In `config.yaml` set:
   ```yaml
   provider: the_odds_api
   executor: betfair
   live: true
   betfair_dry_run: true   # leave true first: matches markets but sends nothing
   ```
4. Run `python run.py run` and **inspect the logs**. The Betfair executor matches
   events/runners to The Odds API by *name*, which is imperfect — verify the
   matched market ids before setting `betfair_dry_run: false`.
5. Only when you're satisfied, set `betfair_dry_run: false` to send real orders.
   Start with a tiny `bankroll`/`max_stake`.

Safety gates: a live executor is only built when `live: true`; any
misconfiguration falls back to paper. `BETTING_LIVE` env var is an extra switch.

## Configuration

All knobs live in `config.yaml` (documented inline). Secrets come from the
environment only (`.env`), never from the committed config. Key settings:
`min_edge`, `devig_method`, `reference_books`, `bankroll`, `kelly_multiplier`,
`max_fraction_per_bet`, `max_total_exposure_fraction`, `executor`, `live`.

## Tests

```bash
python -m unittest discover -s tests -v
```

Covers de-vig math, Kelly/EV, value detection on seeded data, bankroll caps, the
paper executor, the store + settlement, the live-money safety gate, and a full
paper pipeline run.

## Scheduling

`run.py` is a one-shot. To poll continuously, drive it from cron or a loop, e.g.
`*/5 * * * * cd /path && python run.py run` (every 5 minutes). Mind your odds-API
request quota and the bookmaker line-movement between fetch and placement.

## Project layout

```
bot/
  config.py          layered config (defaults < yaml < env)
  models.py          dataclasses: Outcome, BookOdds, MarketBoard, ValueBet, PlacementResult
  devig.py           de-vig methods (multiplicative / additive / shin)
  value.py           ValueDetector + Kelly/EV
  bankroll.py        stake sizing & exposure caps
  providers/         sample (offline) + the_odds_api (live)
  execution/         paper (default) + betfair (real exchange)
  store.py           SQLite + CSV logging, settlement, P&L summary
  bot.py             orchestration + live-money safety gate
run.py               CLI: scan | run | report | settle
tests/               unit + end-to-end tests
```
