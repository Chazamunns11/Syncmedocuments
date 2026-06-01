#!/usr/bin/env python3
"""CLI entrypoint for the value betting bot.

Examples
--------
  # Identify value bets only (no placement), using offline sample data:
  python run.py scan

  # Identify, place (paper by default) and log:
  python run.py run

  # Run continuously, placing each bet as close to kickoff as possible:
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
        print(f"\nFound {len(bets)} value bet(s):\n")
        for b in bets:
            print(f"  [{b.edge*100:5.1f}% edge] {b.matchup} | {b.market} | "
                  f"{b.selection} @ {b.price:.2f} ({b.bookmaker})")
            comm = ""
            if b.commission and b.eff_price:
                comm = f" net {b.eff_price:.2f} after {b.commission*100:.0f}% comm"
            print(f"      fair {b.fair_price:.2f} (p={b.fair_prob:.3f}){comm}  "
                  f"EV/unit {b.ev:+.3f}  Kelly {b.kelly_fraction*100:.2f}%  "
                  f"stake {_fmt_money(b.stake)}")
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
                  f"stake {_fmt_money(bet.stake)} via {r.executor} "
                  f"[{r.external_ref or '-'}] {r.message}")
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
    print(f"Watching continuously in {mode} mode. "
          f"Placing within {cfg.place_window_minutes:.0f} min of kickoff. "
          f"Ctrl-C to stop.")
    try:
        runner.run()
        return 0
    except KeyboardInterrupt:
        print("\nStopping...")
        runner.stop()
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
        print(f"  ROI (settled):  {s['roi']*100:+.2f}%")
        print(f"  avg edge:       {(s['avg_edge'] or 0)*100:+.2f}%")
        if s["clv_n"]:
            print(f"  CLV:            avg {(s['avg_clv'] or 0)*100:+.2f}%  "
                  f"beat close {s['clv_beat']}/{s['clv_n']} "
                  f"({s['clv_beat_rate']*100:.0f}%)")
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
    sub.add_parser("report", help="show logged placements and P&L")
    p_settle = sub.add_parser("settle", help="mark a placed bet WON/LOST/VOID")
    p_settle.add_argument("--ref", required=True, help="external_ref of the placement")
    p_settle.add_argument("--result", required=True, choices=["WON", "LOST", "VOID"])

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )
    cfg = Config.load(args.config)

    if args.command == "scan":
        return cmd_scan(cfg)
    if args.command == "run":
        return cmd_run(cfg)
    if args.command == "watch":
        return cmd_watch(cfg)
    if args.command == "report":
        return cmd_report(cfg)
    if args.command == "settle":
        return cmd_settle(cfg, args.ref, args.result)
    return 1


if __name__ == "__main__":
    sys.exit(main())
