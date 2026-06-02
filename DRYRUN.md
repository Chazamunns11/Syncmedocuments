# Dry-run validation — "is the edge real?" (no money at risk)

The exchange is your only route now, and the edge (if any) is thin. So **prove
it before you stake a penny.** This runs the bot against **live** exchange prices
but places **paper** bets, captures real CLV vs the market close, and gives you a
statistical go/no-go. It costs nothing but time.

## 1. Configure (paper mode, live prices)

Put your keys in `.env` (paper mode never places real money — `live: false`):

```
ODDS_API_KEY=...          # the Pinnacle/consensus "truth" line (UK-accessible)
BETFAIR_USERNAME=...       # needed to READ live exchange prices (not to bet)
BETFAIR_PASSWORD=...
BETFAIR_APP_KEY=...
BETFAIR_CERT_PATH=...
```

In `config.yaml` (these are the defaults that matter for a real dry-run):

```yaml
mode: pinnacle_betfair      # sharp consensus as truth + exchange prices
pinnacle_source: the_odds_api   # Pinnacle isn't UK-available directly
venue_source: betfair       # read real Betfair prices
executor: paper             # PAPER — no real money
live: false                 # safety gate stays closed
block_adverse_sharp_move: true   # don't catch falling knives
```

Sanity-check first: `python run.py doctor`

## 2. Run it continuously near kickoffs

```bash
python run.py go --budget 1000 --stake 10      # paper by default
```

Leave it running (a small VPS or a spare machine is ideal). It polls near
kickoff, places paper bets on value, and at the off it records:
- the **closing market price** → `clv_market` (the real scoreboard)
- the closing model fair price → `clv`

Let it accumulate **at least ~100–300 bets**. That means days-to-weeks across
several leagues/sports — set `pinnacle_sports` / `betfair_event_types` wide
enough to get volume.

## 3. Read the verdict (weekly)

```bash
python run.py validate          # or: --min-bets 200
```

You'll get, for **CLV vs market** (the one that matters):

- ✅ **GO** — mean CLV is significantly positive (95% CI excludes zero). The edge
  looks real → graduate to **tiny real stakes** on Smarkets.
- ⏳ **KEEP COLLECTING** — too few bets, or positive but not yet significant. It
  tells you roughly how many more bets you need.
- 🛑 **NO-GO** — CLV isn't positive. There's no edge on this config; **do not
  stake real money.** Re-tune via `backtest --sweep`/`--validate`, or stop.

`python run.py report` shows the running averages and P&L alongside it.

## 4. Only then, go live (carefully)

If — and only if — CLV-vs-market is a clear GO:
1. Switch to the lowest-cost venue (Smarkets/Matchbook) — commission is your
   biggest lever now that matched betting is gone.
2. Start with **tiny** real stakes; confirm execution + that CLV holds with real
   fills.
3. Scale slowly, **only while CLV stays positive**. Quarter-Kelly, keep the
   circuit breakers on, ring-fence an affordable-to-lose bankroll.

The whole point: the dry-run lets the numbers — not hope — decide whether real
money goes in.
