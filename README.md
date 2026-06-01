# Value Betting Bot — Pinnacle truth → Betfair Exchange

A sports betting bot that **identifies** profitable value bets, **places** them,
and **logs** every one — built for the realistic case where you're limited or
banned on the soft bookmakers.

**The core idea:**
- **Pinnacle is the source of truth.** It's the sharpest mainstream book: it
  prices close to true probability and welcomes winners. We strip its margin
  ("de-vig") to get a **fair probability** for each outcome.
- **Betfair Exchange is where you actually bet.** An exchange doesn't ban or
  limit winners — you bet against other punters and Betfair takes commission on
  net winnings. It also has an **official API that permits automation**.
- **The bet:** wherever Betfair's back price beats Pinnacle's fair price by your
  threshold *after commission*, that's a +EV value bet — place it on Betfair.

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
python run.py run        # identify, place (paper) and log
python run.py report     # logged bets + running P&L
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
| Truth | `bot/pinnacle.py` | Pinnacle line → de-vig → `FairLine` (fair prob per selection). Via The Odds API or direct. |
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

### Why a sharp reference?
Pinnacle prices near true probability and accepts big bets, so its de-vigged line
is the cheapest good estimate of "truth". De-vig methods: `multiplicative`
(default), `additive`, `shin` (favourite–longshot aware) — see `bot/devig.py`.

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

31 tests: de-vig math, Kelly/EV, commission-adjusted value, the Betfair price
ladder, event matching, bankroll caps, paper executor, store + settlement, the
live-money safety gate, and full paper pipelines for both modes.

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
  betfair_client.py  shared Betfair session: prices + placement + price ladder
  matcher.py         pair Pinnacle <-> Betfair events, align runners -> boards
  value.py           ValueDetector + Kelly/EV (commission-aware)
  bankroll.py        stake sizing & exposure caps
  samples.py         offline sample Pinnacle lines + Betfair quotes
  providers/         multi_book feeds: sample + the_odds_api
  execution/         paper (default) + betfair (real exchange)
  store.py           SQLite + CSV logging, settlement, P&L summary
  bot.py             orchestration + live-money safety gate
run.py               CLI: scan | run | report | settle
tests/               unit + end-to-end tests
```
