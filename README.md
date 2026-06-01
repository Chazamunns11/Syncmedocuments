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

## Quick start

```bash
pip install -r requirements.txt        # not needed for the offline/paper demo

python run.py scan       # identify value bets (offline sample data)
python run.py run        # identify, place (paper) and log — one shot
python run.py watch      # run CONTINUOUSLY, placing each bet near kickoff
python run.py report     # logged bets + running P&L + edge + CLV
python run.py settle --ref paper-xxxx --result WON   # settle a finished bet
```

Sample-mode `scan` output:

```
[  6.7% edge] Arsenal vs Chelsea | h2h | Arsenal @ 2.20 (betfair)
    fair 2.01 (p=0.499) net 2.14 after 5% comm  EV/unit +0.067  Kelly 5.86%  stake 14.65
```

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

52 tests: de-vig math (incl. power), Kelly/EV, commission-adjusted value, the
weighted + Kaunitz consensus models and blend, book weighting, the edge haircut /
liquidity / overround filters, liquidity stake cap, the Betfair price ladder,
event matching, the continuous scheduler (window + dedup), store + settlement +
CLV, the live-money safety gate, and full paper pipelines for every truth model.

## Modes

`multi_book` (the original cross-bookmaker scan over a single odds feed) is still
available via `mode: multi_book`. The headline mode is `pinnacle_betfair`.

## Project layout

```
bot/
  config.py          layered config (defaults < yaml < env)
  models.py          dataclasses incl. FairLine, VenueQuote, ValueBet (+ exchange ids)
  devig.py           de-vig methods (multiplicative / additive / shin)
  pinnacle.py        Pinnacle truth source (direct API + via The Odds API)
  consensus.py       weighted Power-Method + Kaunitz consensus truth models
  betfair_client.py  shared Betfair session: prices + placement + cancel + ladder
  matcher.py         pair Pinnacle <-> Betfair events, align runners -> boards
  value.py           ValueDetector + Kelly/EV (commission/haircut/liquidity-aware)
  bankroll.py        stake sizing & exposure caps (+ liquidity cap)
  scheduler.py       continuous near-kickoff runner (adaptive polling + dedup)
  samples.py         offline sample Pinnacle lines + Betfair quotes
  providers/         multi_book feeds: sample + the_odds_api
  execution/         paper (default) + betfair (real exchange)
  store.py           SQLite + CSV logging, settlement, P&L + CLV
  bot.py             orchestration (concurrent fetch) + live-money safety gate
run.py               CLI: scan | run | watch | report | settle
tests/               unit + end-to-end tests
```
