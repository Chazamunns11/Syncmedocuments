# Value Betting Bot — Pinnacle truth → Betfair Exchange

A sports betting bot that **identifies** profitable value bets, **places** them,
and **logs** every one — built for the realistic case where you're limited or
banned on the soft bookmakers.

**The core idea:**
- **A fair probability comes from the market's own numbers.** By default a
  **weighted Power-Method consensus** of many bookmakers (sharp books like
  Pinnacle weighted higher) — the "wisdom of crowds" that, in peer-reviewed work,
  predicts outcomes with R²≈0.99. You can also use Pinnacle alone or the Kaunitz
  α-corrected consensus (`truth_model`).
- **Betfair Exchange is where you actually bet.** An exchange doesn't ban or
  limit winners — you bet against other punters and Betfair takes commission on
  net winnings. It also has an **official API that permits automation**.
- **The bet:** wherever Betfair's back price beats the fair price by your
  threshold *after commission*, that's a +EV value bet — place it on Betfair,
  as close to kickoff as possible.

> Runs out of the box on **offline sample data** in **paper mode** with **zero
> third-party dependencies**. Try it before wiring up any account.

---

## ⚠️ Read this first

1. **Pinnacle left the UK market.** UK customers generally cannot open a Pinnacle
   account or get its API. So the bot can read Pinnacle's line **two ways** — set
   `pinnacle_source`:
   - `the_odds_api` — pull Pinnacle's price via [The Odds API](https://the-odds-api.com)
     (it aggregates Pinnacle). **Works from the UK.** ← recommended for you.
   - `direct` — Pinnacle's own API, if you have a funded account in a supported region.
2. **Betfair is the one mainstream venue you can legitimately automate** and that
   won't ban winners. You need a funded account + an
   [Application Key](https://developer.betfair.com).
3. **+EV is not a guarantee.** Variance is real; bankrolls bust if over-staked.
   You're responsible for local gambling law, account terms, and your own losses.
   Only stake what you can afford to lose, and use your operator's
   responsible-gambling tools. Provided for educational use, no warranty.

The bot **cannot place a real bet** unless you explicitly set `live: true`,
`executor: betfair`, and provide credentials. Everything else is paper.

---

## Everything it does

- **Truth models:** weighted Power-Method consensus (sharp-weighted, recency-aware),
  single-book Pinnacle, Kaunitz α-corrected consensus, or a blend.
- **De-vig:** multiplicative / additive / Shin / power / ensemble.
- **Strict event matching:** alias map + accent/noise normalisation, both-team
  orientation check, ambiguity rejection (won't bet the wrong game).
- **Value engine:** commission-adjusted EV, edge haircut, liquidity & overround
  filters, **expected-CLV gate (+CLV only)**, **one bet per event**.
- **Staking:** fractional Kelly *or* flat stake, capped to bankroll, daily budget,
  open exposure and **available liquidity**; compounding bankroll.
- **Risk:** circuit breakers (drawdown stop-loss, bankroll floor, daily caps,
  open-position cap) that halt betting automatically.
- **Execution:** continuous near-kickoff scheduler, Betfair placement by runner
  id, in-play cancel guard, **auto-settlement from Betfair cleared orders**.
- **CLV:** taken value + expected CLV on every bet; **realised CLV vs the true
  market close** captured automatically at kickoff.
- **Validate before risking money:** backtest on football-data.co.uk history with
  edge-bucket analysis and a **parameter sweep** to find the best settings.
- **Ops:** `doctor` preflight, `status` dashboard, webhook/Slack alerts, retrying
  HTTP, config validation, optional log file, multi-sport (soccer/tennis/…).

## Quick start

```bash
pip install -r requirements.txt        # not needed for the offline/paper demo

# ONE COMMAND TO START BETTING — set your budget and bet size, press go:
python run.py go --budget 1000 --stake 50          # flat £50 per bet
python run.py go --budget 1000 --kelly 0.2         # or 20% Kelly sizing
python run.py go --budget 1000 --stake 50 --live   # place REAL bets on Betfair

# Other commands:
python run.py backtest --data E0.csv      # validate the edge on real history
python run.py backtest --sweep            # find the most profitable settings
python run.py doctor     # preflight checks before going live
python run.py status     # dashboard: bankroll, exposure, risk, CLV
python run.py scan       # just show the value bets (taken value + expected CLV)
python run.py report     # logged bets + P&L + taken value + CLV
python run.py settle --ref paper-xxxx --result WON # settle a finished bet
```

## Go-live runbook (do this in order — don't skip)

The strategy is evidence-based, but profitability is **not** guaranteed and must
be *earned through validation*. Follow this sequence:

1. **Backtest on real data.** Download free season CSVs from
   [football-data.co.uk](https://www.football-data.co.uk/) and run
   `python run.py backtest --data "*.csv"`. Then `--sweep` to find the settings
   with the best **CLV**. If average CLV isn't reliably **positive** here, stop —
   there's no edge to harvest and no staking trick fixes that.
2. **Wire up keys** in `.env` (`ODDS_API_KEY`, `BETFAIR_*`) and run
   `python run.py doctor` until everything is PASS.
3. **Dry-run live for 1–2 weeks**: in `config.yaml` set `pinnacle_source:
   the_odds_api`, `venue_source: betfair`, `executor: betfair`, `live: true`,
   `betfair_dry_run: true`. Run `python run.py go --budget 1000 --stake 10`.
   **Verify every matched event by eye** in the logs and watch the **CLV-vs-market**
   in `report`. This is the real test.
4. **Go live tiny**: set `betfair_dry_run: false` and use `--stake 2`. Confirm
   real fills and that `auto_settle` is settling from Betfair.
5. **Scale slowly** only while CLV-vs-market stays positive over a few hundred
   bets, and account for the **Premium Charge** (`betfair_premium_charge_rate`).

Tip: a lower-commission exchange with **no premium charge** (e.g. Smarkets, ~2%)
materially improves net returns — set `betfair_commission: 0.02` and
`betfair_premium_charge_rate: 0` if you bet there.

## Safety, risk & survival

The bot is built to *survive variance* (the thing that kills most bettors):
- **Circuit breakers** halt betting on a drawdown stop-loss, a bankroll floor, a
  daily stake/bet-count cap, or too many open positions.
- **Stake caps** to daily and open-exposure budgets, and to the liquidity
  actually available (never assumes a better-than-top-of-book fill).
- **Compounding bankroll** grows/shrinks with realised P&L (auto-settled from
  Betfair), so Kelly scales with real results.
- **Config validation + `doctor`** refuse to start live betting on misconfig.
All tunable in `config.yaml` (`stop_loss_fraction`, `daily_stake_limit_fraction`,
`max_open_bets`, `min_bankroll_fraction`, …).

`go` runs continuously: it finds value, places **at most one bet per event** as
close to kickoff as possible, logs the **taken value and expected CLV** of every
bet, and **auto-records the realised CLV** at kickoff. Ctrl-C to stop. Defaults
come from `config.yaml`; the flags just override budget/stake on the fly.

Sample-mode `scan` output (every bet shows **taken value** and **expected CLV**):

```
Arsenal vs Chelsea | h2h | Arsenal @ 2.20 (betfair)
    fair 2.02 (p=0.496) net 2.14 after 5% comm
    taken value +5.20%   expected CLV +9.18%   EV/unit +0.062   stake 50.00
```

### Taken value, expected CLV, and the "+CLV only" rule
- **Taken value** = how much the price you take beats the fair price, *after*
  commission and the haircut — your realised edge on the bet.
- **Expected CLV** = how much the taken price beats the fair (closing-proxy) price
  *gross* of commission — your expected Closing Line Value. The bot **only places
  bets where expected CLV is positive** (`min_expected_clv`, default `0`), so by
  construction every bet is taken at +CLV. Raise it (e.g. `--min-clv 0.02`) to
  demand a bigger CLV cushion.
- **Realised CLV** is captured automatically: the scheduler snapshots the fair
  line ~20s before kickoff and stores `taken_price / closing_fair_price − 1`.
  `report` shows the average and the beat-the-close rate — your real scoreboard.

> Note: you can *target* +CLV on every bet (and we only enter at +expected-CLV),
> but no system can *guarantee* realised CLV — the market can still move after you
> bet. Betting as late as possible (this bot does) keeps taken ≈ closing.

## How it works (mode: `pinnacle_betfair`)

```
 Pinnacle ─┐                                   ┌─▶ BankrollManager ─▶ Betfair ─▶ BetStore
 (fair %)  ├─▶ EventMatcher ─▶ ValueDetector ──┤      (Kelly)         executor    (log+P&L)
 Betfair  ─┘   (pair events)   (+EV net of      └─────────────────────(place)
 (back £)        align runners   commission)
```

| Stage | Module | What it does |
|-------|--------|--------------|
| Truth | `bot/pinnacle.py`, `bot/consensus.py` | Fair probability per selection — Pinnacle, weighted multi-book consensus, or Kaunitz (`truth_model`). |
| Venue | `bot/betfair_client.py` | One Betfair session: best back prices **and** placement, sharing market/selection ids. |
| Match | `bot/matcher.py` | Pair Pinnacle ↔ Betfair events by team-name similarity + start time; align runners; build two-book `MarketBoard`s. |
| Identify | `bot/value.py` + `bot/devig.py` | Fair price from Pinnacle; flag Betfair prices that beat it by ≥ `min_edge` **after commission**; EV + Kelly. |
| Size | `bot/bankroll.py` | Fractional-Kelly stake with per-bet, min/max and total-exposure caps. |
| Place | `bot/execution/` | `BetfairExecutor` (places by the runner's own ids — no fuzzy match) or `PaperExecutor` (safe default). |
| Log | `bot/store.py` | SQLite + CSV of every identified and placed bet; `settle()` → realised P&L / ROI. |

### Commission is built into the value test
A winning back bet at decimal odds `o` returns `(o-1)·(1-commission)` profit. The
detector values the **commission-adjusted** price, so it only fires when the edge
survives Betfair's rake (`betfair_commission`, UK base 5%).

### Truth models (how the fair probability is estimated)
Set `truth_model`:

| Model | Method | Notes |
|-------|--------|-------|
| **`weighted`** (default) | De-vig **each** book with the Power Method, then take a **weighted average** of the probabilities (sharp books weighted higher via `book_weights`). | The practitioner approach; "wisdom of crowds" + sharp anchoring. |
| `pinnacle` | Single sharp book (Pinnacle), de-vigged. | Simple, robust. |
| `consensus` | **Kaunitz et al.**: `p = 1/mean(odds across ≥N books) − α` per outcome. | Faithful to the paper; α is a bias correction. |
| `blend` | Average of `pinnacle` and `weighted`. | Hedge between the two truth signals. |

De-vig methods (`devig_method`): `power` (default) and `shin` both correct
favourite–longshot bias; `multiplicative`/`additive` are simpler baselines.

### Research-backed methodology
This is not guesswork — the strategy mirrors two independent, validated sources:

- **Kaunitz, Zhong & Kreiner (2017), "Beating the bookies with their own
  numbers"** — over **479,440 games** the consensus of bookmaker odds predicted
  outcomes with R²≈0.99; betting when an offered price beat the bias-corrected
  consensus (`odds > 1/(p_cons − α)`, α≈0.05) returned **+3.5%** on closing odds,
  **+9.9%** on pre-kickoff odds, and **+6–8.5% with real money** — until the soft
  books limited their accounts. ([code/data](https://github.com/Lisandro79/BeatTheBookie))
- **A practitioner** running this on Betfair reports **~6% yield on £1M turnover
  since 2023**: *weighted* average of sharp + soft odds → **Power Method** de-vig
  → add own commission → **15–20% Kelly** → monitor Pinnacle to avoid getting
  picked off → *"if you beat CLV consistently you will be profitable long term."*

Every one of those levers is implemented here: weighted Power-Method consensus,
commission-adjusted EV, 15–20% Kelly (`kelly_multiplier: 0.20`), near-kickoff
timing, CLV tracking, and Pinnacle line-move protection (below). Both sources
also confirm **why you bet on the exchange, not the soft books**: the books ban
winners; Betfair doesn't.

### Getting picked off: Pinnacle line-move protection
A resting exchange bet can be "picked off" if the sharp line moves against it
before it's matched. The bot mitigates this two ways:
- **`watch` re-evaluates every cycle on fresh data**, so a bet that's no longer
  +EV is simply not (re)placed; and it places **at the available price** near
  kickoff (designed to match immediately, not rest).
- For live resting orders, `BetfairClient.list_unmatched()` /
  `cancel_orders()` let you pull bets when Pinnacle moves (POD-style). Weight
  Pinnacle heavily in `book_weights` so the consensus tracks the sharp line.

## Continuous operation, timed to kickoff (`run.py watch`)

The single biggest accuracy lever is **when** you bet: the line is sharpest right
before the off. `watch` runs forever and, every cycle:

1. re-evaluates value with **fresh** data,
2. places only bets whose event starts within `place_window_minutes` (and hasn't
   started) — so it always acts on the latest, sharpest prices,
3. **sleeps adaptively** — `poll_interval_seconds` when nothing is near kickoff,
   tightening to `refresh_interval_seconds` once an event enters its window — to
   minimise both API load and the lag between pricing and placement,
4. keeps the Betfair session alive and **never double-bets** the same selection.

```bash
python run.py watch        # Ctrl-C to stop
```

Tune `place_window_minutes` (how close to kickoff to fire) and
`min_seconds_before_start` (stop before in-play turns the market over).

## What makes it accurate

| Lever | Where | Effect |
|-------|-------|--------|
| **Power / Shin de-vig** | `bot/devig.py` | Better fair-probability estimate (favourite–longshot bias corrected). |
| **Commission-adjusted EV** | `bot/value.py` | Only bets when value survives Betfair's rake. |
| **Edge haircut** | `edge_haircut` | Conservative cut for estimation error + slippage; filters thin/spurious value. |
| **Overround band** | `max_overround` | Skips wide, early/illiquid Pinnacle lines that are poor truth estimates. |
| **Liquidity filter + stake cap** | `min_liquidity`, bankroll | Won't bet into thin markets; caps stake to money actually available, so you don't fill at worse prices. |
| **Near-kickoff timing** | `bot/scheduler.py` | Bets on the sharpest line of the day. |
| **CLV tracking** | `store.record_closing()` | Closing Line Value — the best predictor of long-term edge. `report` shows avg CLV and beat-rate. |

**Speed:** Pinnacle and Betfair are fetched concurrently; multiple sports fetch
in parallel; the Betfair catalogue is cached so near-kickoff cycles only re-pull
prices (`refresh_prices`), not the full market list; the session is kept alive
to avoid re-login churn.

### Measuring real edge: CLV
After an event starts, record the closing fair price to see if you beat the
close — positive CLV across many bets is the strongest sign the bot has a real
edge (independent of short-run win/loss variance):

```python
bot.store.record_closing(external_ref, closing_fair_price)  # clv = taken/closing - 1
```

## Going live (real money on Betfair)

1. Fund a Betfair account; get an **Application Key** at
   <https://developer.betfair.com> (certificate login recommended).
2. Get an **Odds API key** (<https://the-odds-api.com>) for the Pinnacle line.
3. `cp .env.example .env`, fill in `ODDS_API_KEY` + `BETFAIR_*`, then
   `set -a; . ./.env; set +a`.
4. In `config.yaml`:
   ```yaml
   pinnacle_source: the_odds_api
   venue_source: betfair
   executor: betfair
   live: true
   betfair_dry_run: true     # leave true first: matches + prices, sends nothing
   ```
5. Run `python run.py run -v` and **inspect the matched events and prices.**
   Pinnacle↔Betfair pairing is by name/time and imperfect — verify before trusting
   it. Tune `match_min_team_score` / `match_start_window_minutes`.
6. Only when satisfied, set `betfair_dry_run: false`. Start with a tiny `bankroll`
   and `max_stake`.

Safety gates: a live executor is built only when `live: true`; anything else
falls back to paper. `BETTING_LIVE=true` is an extra env switch.

## Configuration

All knobs live in `config.yaml` (documented inline); secrets come only from the
environment (`.env`). Key settings: `mode`, `pinnacle_source`, `venue_source`,
`betfair_commission`, `min_edge`, `devig_method`, `bankroll`, `kelly_multiplier`,
`match_min_team_score`, `executor`, `live`.

## Tests

```bash
python -m unittest discover -s tests -v
```

127 tests, pure-stdlib and offline, covering de-vig math (incl. power/ensemble),
Kelly/EV, the consensus models + blend + recency weighting, alias matching &
ambiguity rejection, every detector filter, flat/Kelly staking + caps, expected
& realised CLV, one-bet-per-event, risk circuit breakers, the backtester +
sweep, retrying HTTP, config validation, notifications, multi-sport, and the
**Betfair live path** (placement/price parsing via mocked API objects), plus
CLI smoke tests for every command.

## Modes

`multi_book` (the original cross-bookmaker scan over a single odds feed) is still
available via `mode: multi_book`. The headline mode is `pinnacle_betfair`.

## Project layout

```
bot/
  config.py          layered config (defaults < yaml < env)
  models.py          dataclasses incl. FairLine, VenueQuote, ValueBet (+ exchange ids)
  devig.py           de-vig methods (multiplicative / additive / shin)
  devig.py           de-vig: multiplicative/additive/shin/power/ensemble
  pinnacle.py        Pinnacle truth source (direct API + via The Odds API)
  consensus.py       weighted (Power-Method, recency-weighted) + Kaunitz consensus
  aliases.py         team-name normalisation + alias map + similarity
  matcher.py         strict, alias-aware, ambiguity-rejecting event matching
  value.py           ValueDetector + Kelly/EV (commission/haircut/liquidity/+CLV)
  bankroll.py        Kelly or flat staking + caps (incl. liquidity cap)
  risk.py            circuit breakers + daily/exposure stake caps
  betfair_client.py  one Betfair session: prices + placement + cancel + cleared + ladder
  scheduler.py       continuous near-kickoff runner (adaptive poll, dedup, CLV, auto-settle)
  samples.py         offline sample Pinnacle lines + Betfair quotes + multi-book
  backtest.py        football-data.co.uk loader, run_backtest, edge buckets, sweep
  http.py            retrying HTTP with exponential backoff
  providers/         multi_book feeds: sample + the_odds_api
  execution/         paper (default) + betfair (real exchange)
  store.py           SQLite + CSV: logging, settlement (+ from Betfair), CLV, P&L, meta
  bot.py             orchestration (concurrent fetch) + risk + live-money safety gate
run.py               CLI: go | scan | run | watch | backtest | doctor | status | report | settle
tests/               unit + end-to-end tests
```
