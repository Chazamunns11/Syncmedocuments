# QUICKSTART — run the bot in 3 steps

A working, automated value-betting bot. It finds value bets, places them, logs
them, and tracks CLV. Runs **paper (fake money) by default** — it can't bet real
money until you explicitly switch it on. Do steps 1–3 on **your own machine**
(a spare PC or a cheap always-on VPS), not in a throwaway cloud session.

---

## What you need
- **Python 3.9+**
- **An Odds API key** — free signup at https://the-odds-api.com (the odds feed)
- **A Betfair account + API app key** — https://developer.betfair.com (the venue)

That's it. No Pinnacle subscription, no RapidAPI — the default uses a sharp
soft-book consensus for the signal.

---

## Step 1 — install + add your keys
```bash
pip install -r requirements.txt      # one-time
cp .env.example .env                 # then edit .env and fill in:
```
In `.env`, set just these:
```
ODDS_API_KEY=your_odds_api_key
BETFAIR_USERNAME=your_betfair_username
BETFAIR_PASSWORD=your_betfair_password
BETFAIR_APP_KEY=your_betfair_app_key
```
Load them and sanity-check the wiring:
```bash
set -a; . ./.env; set +a
python run.py --config config.dryrun.yaml doctor
```
`doctor` should report your keys are present and the feeds reachable.

---

## Step 2 — run it (paper money, fully automated)
```bash
python run.py --config config.dryrun.yaml go --budget 1000 --stake 10
```
That's the bot running. Leave it going. Near each kickoff it:
1. pulls the odds, 2. finds the highest-CLV value bets, 3. places them (paper),
4. logs them and captures CLV at kickoff. Hands-off.

Check on it any time:
```bash
python run.py --config config.dryrun.yaml report      # bets placed + P&L
```
Tip: run it under `tmux`/`screen` (or as a service) so it keeps running when you
log out. It also prints a "truth-feed freshness" line so you can see the odds are
arriving fresh.

---

## Step 3 — after ~2 weeks, is the edge real?
```bash
python run.py --config config.dryrun.yaml validate
```
Read the **CLV vs MARKET** verdict:
- ✅ **GO** — the edge is real. Go live (below), start with tiny stakes.
- ⏳ **KEEP COLLECTING** — not enough bets yet; let it run longer.
- 🛑 **NO-GO** — no edge on this setup. Don't bet real money. (This is the bot
  doing its job — saving you money.)

---

## Going live (only after a GO)
Edit `config.dryrun.yaml` and change two lines:
```yaml
executor: betfair
live: true
```
Then run the **same** command again — it now places **real** bets:
```bash
python run.py --config config.dryrun.yaml go --budget 1000 --stake 10
```
Start with small stakes. Keep checking `validate`/`report`. If CLV stays
positive, scale up slowly. If it stops being positive, stop.

---

## Safety rules (read once)
- It **cannot** bet real money unless BOTH `executor: betfair` AND `live: true`.
- It bets **at most one bet per event**, sized small, with circuit breakers that
  halt betting on a bad run.
- Only ever stake money you can afford to lose. This is gambling.
- Judge it by **CLV**, not short-term profit — CLV is the signal, profit is noisy.

## Handy commands
```bash
python run.py --config config.dryrun.yaml scan      # show value bets, place nothing
python run.py --config config.dryrun.yaml status    # bankroll / exposure / risk
python run.py --config config.dryrun.yaml report     # placements + P&L + CLV
python run.py --config config.dryrun.yaml validate   # is the edge real?
python -m unittest discover -s tests                 # run the test suite
```
