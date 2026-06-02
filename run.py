#!/usr/bin/env python3
"""CLI entrypoint for the value betting bot.

Examples
--------
  # ONE COMMAND: set your budget + bet size and start betting continuously.
  python run.py go --budget 1000 --stake 50          # flat 50 per bet
  python run.py go --budget 1000 --kelly 0.2         # or 20% Kelly
  python run.py go --budget 1000 --stake 50 --live   # real bets on Betfair

  # Identify value bets only (no placement), using offline sample data:
  python run.py scan

  # Identify, place (paper by default) and log:
  python run.py run

  # Run continuously using config.yaml settings (same engine as `go`):
  python run.py watch

  # Show logged placements and running P&L:
  python run.py report

  # Settle a placed bet once the event finishes:
  python run.py settle --ref paper-abc123 --result WON

Real-money placement requires `live: true` + `executor: betfair` in config and
valid Betfair credentials in the environment. See README.md.
"""
from __future__ import annotations

import argparse
import logging
import sys

from bot.bot import ValueBettingBot
from bot.config import Config


def _fmt_money(x) -> str:
    return f"{x:,.2f}" if x is not None else "-"


def cmd_scan(cfg: Config) -> int:
    bot = ValueBettingBot(cfg)
    try:
        bets = bot.scan()
        if not bets:
            print("No value bets found.")
            return 0
        print(f"\nFound {len(bets)} value bet(s) (max one per event):\n")
        for b in bets:
            print(f"  {b.matchup} | {b.market} | {b.selection} @ {b.price:.2f} "
                  f"({b.bookmaker})")
            comm = ""
            if b.commission and b.eff_price:
                comm = f" net {b.eff_price:.2f} after {b.commission*100:.0f}% comm"
            print(f"      fair {b.fair_price:.2f} (p={b.fair_prob:.3f}){comm}")
            move = ""
            if b.sharp_move is not None:
                arrow = "→toward" if b.sharp_move > 0 else ("→away" if b.sharp_move < 0 else "flat")
                move = f"   sharp {arrow} {b.sharp_move*100:+.1f}pp"
            print(f"      taken value {b.edge*100:+.2f}%   "
                  f"expected CLV {b.exp_clv*100:+.2f}%   "
                  f"EV/unit {b.ev:+.3f}   stake {_fmt_money(b.stake)}{move}")
        return 0
    finally:
        bot.close()


def cmd_run(cfg: Config) -> int:
    bot = ValueBettingBot(cfg)
    try:
        mode = "LIVE" if (cfg.live and cfg.executor == "betfair") else "PAPER"
        print(f"Running in {mode} mode (executor={cfg.executor}, live={cfg.live})")
        results = bot.run()
        if not results:
            print("No value bets to place.")
            return 0
        placed = sum(1 for _, r in results if r.ok)
        print(f"\nPlaced/simulated {placed}/{len(results)} bet(s):\n")
        for bet, r in results:
            print(f"  {r.status:8s} {bet.selection} @ {bet.price:.2f} "
                  f"stake {_fmt_money(bet.stake)} | value {bet.edge*100:+.2f}% "
                  f"exp-CLV {bet.exp_clv*100:+.2f}% via {r.executor} "
                  f"[{r.external_ref or '-'}]")
        return 0
    finally:
        bot.close()


def cmd_watch(cfg: Config) -> int:
    from bot.scheduler import ContinuousRunner
    bot = ValueBettingBot(cfg)
    runner = ContinuousRunner(
        bot,
        poll_interval=cfg.poll_interval_seconds,
        refresh_interval=cfg.refresh_interval_seconds,
        place_window_minutes=cfg.place_window_minutes,
        min_seconds_before_start=cfg.min_seconds_before_start,
    )
    mode = "LIVE" if (cfg.live and cfg.executor == "betfair") else "PAPER"
    if cfg.flat_stake is not None:
        staking = f"flat {_fmt_money(cfg.flat_stake)}/bet"
    else:
        staking = f"{cfg.kelly_multiplier*100:.0f}% Kelly"
    print("=" * 64)
    print(f"  Value betting bot — GO  [{mode}]")
    print(f"  budget {_fmt_money(cfg.bankroll)} | staking {staking} | "
          f"max {_fmt_money(cfg.max_stake)}/bet")
    print(f"  truth: {cfg.truth_model} | only +CLV bets | max ONE bet per event")
    print(f"  placing within {cfg.place_window_minutes:.0f} min of kickoff. "
          f"Ctrl-C to stop.")
    print("=" * 64)
    try:
        runner.run()
        return 0
    except KeyboardInterrupt:
        print("\nStopping...")
        runner.stop()
        return 0
    finally:
        bot.close()


def cmd_go(cfg: Config, args) -> int:
    """One-command start: apply budget/stake overrides, then bet continuously."""
    if args.budget is not None:
        cfg.bankroll = args.budget
    if args.kelly is not None:
        cfg.kelly_multiplier = args.kelly
    if args.stake is not None:
        cfg.flat_stake = args.stake
    if args.max_stake is not None:
        cfg.max_stake = args.max_stake
    if args.min_clv is not None:
        cfg.min_expected_clv = args.min_clv
    if args.live:
        cfg.live = True
        cfg.executor = "betfair"
    # Re-validate AFTER applying the flags (e.g. --live), and refuse to start
    # real betting on any ERROR.
    errors = [m for m in cfg.validate() if m.startswith("ERROR")]
    for m in errors:
        print(f"  config: {m}")
    if errors:
        print("Refusing to start: fix the ERROR(s) above.")
        return 2
    return cmd_watch(cfg)


def cmd_backtest(cfg: Config, args) -> int:
    """Validate the strategy on historical data before risking money."""
    from bot.backtest import (load_football_data, run_backtest, format_result,
                              synthetic_rows, sweep, format_sweep,
                              walk_forward, format_walk_forward)
    if args.data:
        rows = load_football_data(args.data)
        print(f"Loaded {len(rows)} historical matches from {len(args.data)} path(s).")
    else:
        rows = synthetic_rows(n=args.synthetic)
        print(f"No --data given; running on {len(rows)} SYNTHETIC matches "
              f"(demo only, not real evidence).")
    if not rows:
        print("No usable rows found.")
        return 1
    if args.validate:
        print("Walk-forward: optimising on train, validating out-of-sample...")
        print(format_walk_forward(*walk_forward(rows)))
        return 0
    if args.sweep:
        print("Sweeping parameters to find the most profitable configuration...")
        print(format_sweep(sweep(rows)))
        return 0
    res = run_backtest(
        rows, method=cfg.truth_model if cfg.truth_model in ("weighted", "consensus")
        else "weighted",
        min_edge=cfg.min_edge, commission=args.commission,
        devig_method=cfg.devig_method, consensus_alpha=cfg.consensus_alpha,
        book_weights=cfg.book_weights, min_books=cfg.consensus_min_books,
        flat_stake=(args.stake if args.stake else None),
        bankroll=cfg.bankroll, kelly_multiplier=cfg.kelly_multiplier,
        edge_haircut=cfg.edge_haircut)
    print(format_result(res))
    return 0


def cmd_doctor(cfg: Config) -> int:
    """Preflight checks: deps, config, credentials, connectivity, data, matching.
    Run this before going live."""
    ok = "PASS"; warn = "WARN"; fail = "FAIL"
    results = []

    def check(name, status, detail=""):
        results.append((name, status, detail))

    # 1) Config.
    problems = cfg.validate()
    errs = [m for m in problems if m.startswith("ERROR")]
    check("config", fail if errs else ok,
          "; ".join(errs) if errs else f"{len(problems)} note(s)")

    # 2) Dependencies for the selected modes.
    def has(mod):
        try:
            __import__(mod); return True
        except ImportError:
            return False
    if cfg.pinnacle_source == "the_odds_api" or cfg.truth_model in ("weighted", "consensus", "blend"):
        if cfg.pinnacle_source != "sample":
            check("requests (odds API)", ok if has("requests") else fail,
                  "" if has("requests") else "pip install requests")
    if cfg.live and cfg.executor == "betfair":
        check("betfairlightweight", ok if has("betfairlightweight") else fail,
              "" if has("betfairlightweight") else "pip install betfairlightweight")

    # 3) Credentials.
    if cfg.pinnacle_source == "the_odds_api" or cfg.truth_model != "pinnacle":
        if cfg.pinnacle_source != "sample":
            check("ODDS_API_KEY", ok if cfg.odds_api_key else fail,
                  "" if cfg.odds_api_key else "set ODDS_API_KEY in .env")
    if cfg.live and cfg.executor == "betfair":
        have = all([cfg.betfair_username, cfg.betfair_password, cfg.betfair_app_key])
        check("Betfair credentials", ok if have else fail,
              "" if have else "set BETFAIR_USERNAME/PASSWORD/APP_KEY")

    # 4) Connectivity + data (best-effort).
    bot = ValueBettingBot(cfg)
    try:
        try:
            fair = bot._fair_lines()
            check("truth feed", ok if fair else warn,
                  f"{len(fair)} fair line(s)")
        except Exception as exc:
            check("truth feed", fail, str(exc)[:80])
        try:
            quotes = bot._venue_quotes()
            check("venue feed", ok if quotes else warn,
                  f"{len(quotes)} quote(s)")
        except Exception as exc:
            check("venue feed", fail, str(exc)[:80])
        try:
            boards = bot._boards()
            check("event matching", ok if boards else warn,
                  f"{len(boards)} matched event(s)")
        except Exception as exc:
            check("event matching", fail, str(exc)[:80])
    finally:
        bot.close()

    print("\n=== Preflight (doctor) ===")
    worst = ok
    for name, status, detail in results:
        mark = {"PASS": "✓", "WARN": "!", "FAIL": "✗"}[status]
        print(f"  [{mark}] {name:24s} {status}{('  — ' + detail) if detail else ''}")
        if status == fail:
            worst = fail
        elif status == warn and worst != fail:
            worst = warn
    if cfg.pinnacle_source == "sample":
        print("  NOTE: running on SAMPLE data — switch pinnacle_source to "
              "the_odds_api and venue_source to betfair for real betting.")
    print(f"\n  Overall: {worst}")
    return 0 if worst != fail else 1


def cmd_status(cfg: Config) -> int:
    """Live dashboard: bankroll, exposure, today's activity, risk state, CLV."""
    bot = ValueBettingBot(cfg)
    try:
        store = bot.store
        bankroll = bot.bankroll.bankroll
        peak = store.get_meta("peak_bankroll", cfg.bankroll)
        realised = store.realised_profit()
        ok, reason = bot.risk.status(bankroll)
        import datetime as _dt
        day = _dt.datetime.now(_dt.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0).isoformat()
        s = store.summary()
        print("\n=== Bot status ===")
        print(f"  bankroll:       {_fmt_money(bankroll)} "
              f"(start {_fmt_money(cfg.bankroll)}, realised {_fmt_money(realised)})")
        dd = (peak - bankroll) / peak * 100 if peak > 0 else 0.0
        print(f"  peak / drawdown:{_fmt_money(peak)} / {dd:.1f}%")
        print(f"  open positions: {store.count_open()}  "
              f"exposure {_fmt_money(store.open_exposure())}")
        print(f"  today:          {store.count_since(day)} bets, "
              f"{_fmt_money(store.staked_since(day))} staked")
        print(f"  risk state:     {'OK — betting enabled' if ok else 'HALTED: ' + reason}")
        print(f"  lifetime:       {s['n']} bets, P&L {_fmt_money(s['profit'])}, "
              f"ROI {s['roi']*100:+.2f}%")
        if s["clv_mkt_n"]:
            print(f"  CLV vs market:  avg {(s['avg_clv_market'] or 0)*100:+.2f}%  "
                  f"beat {s['clv_mkt_beat']}/{s['clv_mkt_n']}")
        elif s["clv_n"]:
            print(f"  CLV vs model:   avg {(s['avg_clv'] or 0)*100:+.2f}%  "
                  f"beat {s['clv_beat']}/{s['clv_n']}")
        return 0
    finally:
        bot.close()


def cmd_report(cfg: Config) -> int:
    bot = ValueBettingBot(cfg)
    try:
        s = bot.store.summary()
        print("\n=== Betting summary ===")
        print(f"  placements:     {s['n']}")
        print(f"  total staked:   {_fmt_money(s['staked'])}")
        print(f"  settled:        won {s['won']}  lost {s['lost']}  pending {s['pending']}")
        print(f"  realised P&L:   {_fmt_money(s['profit'])}")
        pc_rate = getattr(cfg, "betfair_premium_charge_rate", 0.0)
        if pc_rate > 0 and s["profit"] > 0:
            premium = pc_rate * s["profit"]
            print(f"  Premium Charge: -{_fmt_money(premium)} ({pc_rate*100:.0f}%)")
            print(f"  net of premium: {_fmt_money(s['profit'] - premium)}")
        print(f"  ROI (settled):  {s['roi']*100:+.2f}%")
        print(f"  avg taken value:{(s['avg_edge'] or 0)*100:+.2f}%")
        print(f"  avg exp CLV:    {(s['avg_exp_clv'] or 0)*100:+.2f}%")
        if s["clv_n"]:
            print(f"  CLV vs model:   avg {(s['avg_clv'] or 0)*100:+.2f}%  "
                  f"beat {s['clv_beat']}/{s['clv_n']} "
                  f"({s['clv_beat_rate']*100:.0f}%)")
        if s["clv_mkt_n"]:
            print(f"  CLV vs market:  avg {(s['avg_clv_market'] or 0)*100:+.2f}%  "
                  f"beat {s['clv_mkt_beat']}/{s['clv_mkt_n']} "
                  f"({s['clv_mkt_beat_rate']*100:.0f}%)   <- the real scoreboard")
        if not s["clv_n"] and not s["clv_mkt_n"]:
            print("  CLV:            (none captured yet — recorded at kickoff)")
        print("\n=== Recent placements ===")
        for row in bot.store.recent_placements(limit=20):
            print(f"  {row['placed_at'][:19]} {row['status']:8s} "
                  f"stake {_fmt_money(row['requested_stake'])} @ "
                  f"{row['requested_price']:.2f} {row['settlement']:7s} "
                  f"P&L {_fmt_money(row['profit'])} [{row['external_ref'] or '-'}]")
        return 0
    finally:
        bot.close()


def cmd_settle(cfg: Config, ref: str, result: str) -> int:
    bot = ValueBettingBot(cfg)
    try:
        profit = bot.store.settle(ref, result)
        if profit is None:
            print(f"No placement found with external_ref={ref}")
            return 1
        print(f"Settled {ref} as {result.upper()}: P&L {_fmt_money(profit)}")
        return 0
    finally:
        bot.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Value sportsbook betting bot")
    parser.add_argument("--config", default="config.yaml", help="path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("scan", help="identify value bets only")
    sub.add_parser("run", help="identify, place and log value bets (one shot)")
    sub.add_parser("watch", help="run continuously, placing bets near kickoff")
    # `go`: one command to start betting. Set budget/stake and press go.
    p_go = sub.add_parser("go", help="set budget/stake and start betting continuously")
    p_go.add_argument("--budget", type=float, help="bankroll / budget")
    p_go.add_argument("--kelly", type=float, help="Kelly fraction, e.g. 0.2 (15-20%%)")
    p_go.add_argument("--stake", type=float,
                      help="FIXED stake per bet (overrides Kelly)")
    p_go.add_argument("--max-stake", type=float, help="max stake per bet")
    p_go.add_argument("--min-clv", type=float,
                      help="min expected CLV to bet, e.g. 0.01 (default 0 = >0)")
    p_go.add_argument("--live", action="store_true",
                      help="place REAL bets on Betfair (default: paper)")
    p_bt = sub.add_parser("backtest", help="validate the strategy on historical data")
    p_bt.add_argument("--data", nargs="*", help="football-data.co.uk CSV path(s)/globs")
    p_bt.add_argument("--commission", type=float, default=0.0,
                      help="exchange commission to apply, e.g. 0.05")
    p_bt.add_argument("--stake", type=float, default=1.0,
                      help="flat stake per bet (0 = use Kelly)")
    p_bt.add_argument("--synthetic", type=int, default=400,
                      help="number of synthetic matches if no --data")
    p_bt.add_argument("--sweep", action="store_true",
                      help="grid-search parameters and rank by CLV/yield")
    p_bt.add_argument("--validate", action="store_true",
                      help="walk-forward: tune on train, report honest out-of-sample edge")
    sub.add_parser("report", help="show logged placements and P&L")
    sub.add_parser("status", help="dashboard: bankroll, exposure, risk, CLV")
    sub.add_parser("doctor", help="preflight checks before going live")
    p_settle = sub.add_parser("settle", help="mark a placed bet WON/LOST/VOID")
    p_settle.add_argument("--ref", required=True, help="external_ref of the placement")
    p_settle.add_argument("--result", required=True, choices=["WON", "LOST", "VOID"])

    args = parser.parse_args(argv)
    handlers = [logging.StreamHandler()]
    cfg = Config.load(args.config)
    if cfg.log_file:
        handlers.append(logging.FileHandler(cfg.log_file))
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )

    # Surface configuration problems; refuse to start live betting on errors.
    problems = cfg.validate()
    errors = [m for m in problems if m.startswith("ERROR")]
    for m in problems:
        print(f"  config: {m}")
    if errors and args.command in ("go", "watch", "run"):
        print("Refusing to start: fix the ERROR(s) above.")
        return 2

    if args.command == "scan":
        return cmd_scan(cfg)
    if args.command == "run":
        return cmd_run(cfg)
    if args.command == "watch":
        return cmd_watch(cfg)
    if args.command == "go":
        return cmd_go(cfg, args)
    if args.command == "backtest":
        return cmd_backtest(cfg, args)
    if args.command == "report":
        return cmd_report(cfg)
    if args.command == "status":
        return cmd_status(cfg)
    if args.command == "doctor":
        return cmd_doctor(cfg)
    if args.command == "settle":
        return cmd_settle(cfg, args.ref, args.result)
    return 1


if __name__ == "__main__":
    sys.exit(main())
