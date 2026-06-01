"""Backtest / validation harness — prove the edge before risking money.

Runs the SAME consensus + value-detection + staking code as the live bot over
historical football matches, and reports profit, yield, hit rate, max drawdown
and — crucially — Closing Line Value against the bookmakers' own closing odds.

Data: free CSVs from https://www.football-data.co.uk/ (e.g. season files like
E0.csv). They contain opening odds across many bookmakers (B365, Pinnacle 'PS',
William Hill 'WH', ...) AND closing odds ('PSC*' = Pinnacle closing), plus the
full-time result 'FTR' (H/D/A) — everything needed to measure real CLV.

Usage:
    from bot.backtest import load_football_data, run_backtest, format_result
    rows = load_football_data(["E0.csv", "D1.csv"])
    print(format_result(run_backtest(rows, method="weighted", min_edge=0.02)))

The conclusion that matters: a positive average CLV across thousands of bets is
the strongest evidence the strategy has a real, durable edge.
"""
from __future__ import annotations

import csv
import glob
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .bankroll import BankrollManager
from .consensus import consensus_lines_from_boards
from .models import BookOdds, MarketBoard, Outcome
from .value import ValueDetector

# Result code -> selection role.
_RESULT_ROLE = {"H": "home", "D": "draw", "A": "away"}


def load_football_data(paths: List[str]) -> List[dict]:
    """Load one or more football-data.co.uk CSV files (globs allowed)."""
    rows: List[dict] = []
    files: List[str] = []
    for p in paths:
        files.extend(sorted(glob.glob(p)) or [p])
    for f in files:
        with open(f, newline="", encoding="latin-1") as fh:
            for row in csv.DictReader(fh):
                if row.get("HomeTeam") and row.get("FTR") in _RESULT_ROLE:
                    rows.append(row)
    return rows


def _to_float(x) -> Optional[float]:
    try:
        v = float(x)
        return v if v > 1.0 else None
    except (TypeError, ValueError):
        return None


def _discover_books(row: dict, closing: bool) -> Dict[str, Tuple[float, float, float]]:
    """Find {prefix: (H,D,A)} odds triples in a row. ``closing`` selects the
    closing columns vs opening ones.

    A column is a CLOSING column only if its prefix ends in 'C' AND the prefix
    without that 'C' is itself a book (PSC->PS, B365C->B365). This avoids
    misreading books that merely end in 'C' such as 'VC' (VC Bet)."""
    triples: Dict[str, Tuple[float, float, float]] = {}
    for key in row:
        if not key.endswith("H") or len(key) < 2:
            continue
        prefix = key[:-1]
        if "AH" in prefix or prefix in ("FT", "HT"):  # skip handicap/score cols
            continue
        h = _to_float(row.get(prefix + "H"))
        d = _to_float(row.get(prefix + "D"))
        a = _to_float(row.get(prefix + "A"))
        if h and d and a:
            booksum = 1 / h + 1 / d + 1 / a
            if 1.0 <= booksum <= 1.6:  # sane 1X2 overround
                triples[prefix] = (h, d, a)
    all_prefixes = set(triples)
    out = {}
    for prefix, o in triples.items():
        is_closing = prefix.endswith("C") and prefix[:-1] in all_prefixes
        if is_closing == closing:
            out[prefix] = o
    return out


def _board_from_books(home, away, when, books: Dict[str, Tuple]) -> MarketBoard:
    bk = [BookOdds(prefix, "h2h",
                   [Outcome(home, o[0]), Outcome("Draw", o[1]), Outcome(away, o[2])])
          for prefix, o in books.items()]
    return MarketBoard("bt", "soccer", when, home, away, "h2h", books=bk)


@dataclass
class BacktestResult:
    bets: int = 0
    staked: float = 0.0
    profit: float = 0.0
    wins: int = 0
    yield_pct: float = 0.0
    hit_rate: float = 0.0
    avg_edge: float = 0.0
    avg_odds: float = 0.0
    avg_clv: Optional[float] = None
    clv_positive_rate: Optional[float] = None
    max_drawdown: float = 0.0
    final_bankroll: float = 0.0
    starting_bankroll: float = 0.0
    equity_curve: List[float] = field(default_factory=list)
    skipped_no_books: int = 0
    buckets: dict = field(default_factory=dict)  # edge bucket -> stats


_BUCKETS = [(0.0, 0.02), (0.02, 0.04), (0.04, 0.06), (0.06, 0.10), (0.10, 1e9)]


def _bucket_label(edge: float) -> str:
    for lo, hi in _BUCKETS:
        if lo <= edge < hi:
            return f"{lo*100:.0f}-{hi*100:.0f}%" if hi < 1e9 else f"{lo*100:.0f}%+"
    return "?"


def run_backtest(
    rows: List[dict],
    method: str = "weighted",
    min_edge: float = 0.02,
    commission: float = 0.0,
    devig_method: str = "power",
    consensus_alpha: float = 0.05,
    book_weights: Optional[Dict[str, float]] = None,
    min_books: int = 3,
    flat_stake: Optional[float] = 1.0,
    bankroll: float = 1000.0,
    kelly_multiplier: float = 0.2,
    max_stake: float = 1e9,
    edge_haircut: float = 0.0,
) -> BacktestResult:
    """Simulate the strategy over historical rows. Bets at the BEST available
    opening price across books when it beats the consensus fair price; settles
    on the actual result; measures CLV against the closing (Pinnacle) line."""
    alpha = {r: consensus_alpha for r in ("home", "draw", "away")}
    # Weight sharp books (incl. football-data's Pinnacle code 'PS') up unless the
    # caller overrode the weights with sharp codes already.
    bw = {k.lower(): v for k, v in (book_weights or {}).items()}
    bw.setdefault("ps", 3.0)
    bw.setdefault("pinnacle", 3.0)
    bw.setdefault("b365", 1.5)
    bw.setdefault("_default", 1.0)
    book_weights = bw
    detector = ValueDetector(commission=commission, min_edge=min_edge,
                             devig_method=devig_method, one_per_event=True,
                             min_liquidity=0.0, max_overround=1.6,
                             edge_haircut=edge_haircut, min_price=1.01,
                             max_price=1000.0)
    bank = BankrollManager(bankroll=bankroll, kelly_multiplier=kelly_multiplier,
                           max_fraction_per_bet=1.0, min_stake=0.0,
                           max_stake=max_stake, max_total_exposure_fraction=1e9,
                           flat_stake=flat_stake, round_to=0.0)
    res = BacktestResult(starting_bankroll=bankroll, final_bankroll=bankroll)
    running = bankroll
    peak = bankroll
    edges, clvs, odds_list = [], [], []

    for row in rows:
        home, away = row["HomeTeam"], row["AwayTeam"]
        when = row.get("Date", "")
        open_books = _discover_books(row, closing=False)
        if len(open_books) < min_books:
            res.skipped_no_books += 1
            continue
        board = _board_from_books(home, away, when, open_books)
        fair_lines = consensus_lines_from_boards(
            [board], method=method, book_weights=book_weights,
            devig_method=devig_method, alpha=alpha, min_books=min_books)
        if not fair_lines:
            continue
        fl = fair_lines[0]
        # "Venue" = the best available opening price per selection.
        best = {}
        for prefix, (h, d, a) in open_books.items():
            for name, o in ((home, h), ("Draw", d), (away, a)):
                best[name] = max(best.get(name, 0.0), o)
        venue = BookOdds("best", "h2h", [Outcome(n, o) for n, o in best.items()])
        board.books = [venue]
        board.fair_probs = dict(fl.probs)
        board.fair_source = fl.source
        board.overround = fl.overround

        bets = detector.detect([board])
        if not bets:
            continue
        bet = bets[0]  # one per event

        stake = bank.stake_for(bet)
        if stake <= 0:
            continue

        # Settle on the real result.
        won_role = _RESULT_ROLE[row["FTR"]]
        won_name = {"home": home, "draw": "Draw", "away": away}[won_role]
        win = (bet.selection == won_name)
        gross = bet.price - 1.0
        profit = stake * gross * (1.0 - commission) if win else -stake

        # CLV vs the closing (Pinnacle) line, if present.
        clv = None
        close_books = _discover_books(row, closing=True)
        if len(close_books) >= 1:
            cboard = _board_from_books(home, away, when, close_books)
            cfl = consensus_lines_from_boards(
                [cboard], method=method, book_weights=book_weights,
                devig_method=devig_method, alpha=alpha, min_books=1)
            if cfl and cfl[0].probs.get(bet.selection):
                closing_fair = 1.0 / cfl[0].probs[bet.selection]
                clv = bet.price / closing_fair - 1.0
                clvs.append(clv)

        res.bets += 1
        res.staked += stake
        res.profit += profit
        res.wins += 1 if win else 0
        edges.append(bet.edge)
        odds_list.append(bet.price)
        # Per-edge-bucket breakdown (where does the edge actually live?).
        b = res.buckets.setdefault(_bucket_label(bet.edge),
                                   {"bets": 0, "staked": 0.0, "profit": 0.0,
                                    "clv_sum": 0.0, "clv_n": 0, "clv_pos": 0})
        b["bets"] += 1
        b["staked"] += stake
        b["profit"] += profit
        if clv is not None:
            b["clv_sum"] += clv
            b["clv_n"] += 1
            b["clv_pos"] += 1 if clv > 0 else 0
        running += profit
        peak = max(peak, running)
        res.max_drawdown = max(res.max_drawdown, peak - running)
        res.equity_curve.append(running)

    res.final_bankroll = running
    if res.bets:
        res.yield_pct = res.profit / res.staked * 100 if res.staked else 0.0
        res.hit_rate = res.wins / res.bets
        res.avg_edge = statistics.mean(edges)
        res.avg_odds = statistics.mean(odds_list)
    if clvs:
        res.avg_clv = statistics.mean(clvs)
        res.clv_positive_rate = sum(1 for c in clvs if c > 0) / len(clvs)
    return res


def format_result(r: BacktestResult) -> str:
    lines = [
        "=== Backtest result ===",
        f"  bets:            {r.bets}",
        f"  staked:          {r.staked:,.2f}",
        f"  profit:          {r.profit:+,.2f}",
        f"  yield:           {r.yield_pct:+.2f}%",
        f"  hit rate:        {r.hit_rate*100:.1f}%",
        f"  avg odds:        {r.avg_odds:.2f}",
        f"  avg taken value: {r.avg_edge*100:+.2f}%",
    ]
    if r.avg_clv is not None:
        lines.append(f"  avg CLV:         {r.avg_clv*100:+.2f}%  "
                     f"(+CLV {r.clv_positive_rate*100:.0f}% of bets)  <- key metric")
    lines += [
        f"  max drawdown:    {r.max_drawdown:,.2f}",
        f"  bankroll:        {r.starting_bankroll:,.2f} -> {r.final_bankroll:,.2f}",
    ]
    if r.skipped_no_books:
        lines.append(f"  (skipped {r.skipped_no_books} rows with too few books)")
    if r.buckets:
        lines.append("  by taken-value bucket:")
        for label, _ in [(f"{lo*100:.0f}-{hi*100:.0f}%" if hi < 1e9
                          else f"{lo*100:.0f}%+", None) for lo, hi in _BUCKETS]:
            b = r.buckets.get(label)
            if not b:
                continue
            y = b["profit"] / b["staked"] * 100 if b["staked"] else 0.0
            clv = (b["clv_sum"] / b["clv_n"] * 100) if b["clv_n"] else 0.0
            lines.append(f"    {label:>7}: {b['bets']:5d} bets  "
                         f"yield {y:+6.2f}%  CLV {clv:+6.2f}%")
    return "\n".join(lines)


def sweep(rows: List[dict], grid: Optional[dict] = None, top: int = 8) -> List:
    """Grid-search strategy parameters on historical data and rank by average
    CLV then yield. Returns a list of (params, BacktestResult) best-first — so you
    can pick the most robust, highest-edge configuration before going live."""
    import itertools

    grid = grid or {
        "method": ["weighted", "kaunitz"],
        "min_edge": [0.01, 0.02, 0.03, 0.04],
        "devig_method": ["power", "shin"],
        "consensus_alpha": [0.03, 0.05, 0.07],
    }
    keys = list(grid)
    results = []
    for combo in itertools.product(*(grid[k] for k in keys)):
        params = dict(zip(keys, combo))
        res = run_backtest(rows, flat_stake=1.0, **params)
        if res.bets >= 20:  # ignore configs with too few bets to be meaningful
            results.append((params, res))

    def score(item):
        _, r = item
        return (r.avg_clv if r.avg_clv is not None else -1, r.yield_pct)

    results.sort(key=score, reverse=True)
    return results[:top]


def format_sweep(ranked: List) -> str:
    lines = ["=== Parameter sweep (best by CLV, then yield) ==="]
    for params, r in ranked:
        p = " ".join(f"{k}={v}" for k, v in params.items())
        clv = f"{r.avg_clv*100:+.2f}%" if r.avg_clv is not None else "n/a"
        lines.append(f"  CLV {clv:>7}  yield {r.yield_pct:+6.2f}%  "
                     f"bets {r.bets:5d}  | {p}")
    return "\n".join(lines)


def synthetic_rows(n: int = 400, edge: float = 0.03, seed: int = 7) -> List[dict]:
    """Generate synthetic football-data-style rows with a known exploitable edge,
    for offline testing/demo. Many books price near fair; ONE soft book (VC)
    systematically over-prices the home side by ``edge``. Outcomes follow the
    true probabilities, and the closing (PSC) line sits at fair — so measured CLV
    is honest. With many books the outlier barely moves the consensus, mirroring
    the real market (~15-30 books)."""
    import random
    rng = random.Random(seed)

    def odds(p, margin):
        return round(1.0 / (p * (1 + margin)), 2)

    rows = []
    # Sharp-ish books with small margins (Pinnacle tightest).
    sharp = {"B365": 0.05, "PS": 0.02, "WH": 0.06, "BW": 0.05, "IW": 0.06,
             "LB": 0.06, "SB": 0.07, "GB": 0.06}
    for i in range(n):
        ph = rng.uniform(0.35, 0.6)
        pd = rng.uniform(0.2, 0.3)
        pa = max(0.05, 1 - ph - pd)
        tot = ph + pd + pa
        ph, pd, pa = ph / tot, pd / tot, pa / tot
        row = {"Date": f"01/01/20{10 + i % 9}", "HomeTeam": f"Home{i}",
               "AwayTeam": f"Away{i}"}
        for code, m in sharp.items():
            # Small per-book noise so books aren't identical.
            j = rng.uniform(-0.01, 0.01)
            row[code + "H"] = odds(ph, m + j)
            row[code + "D"] = odds(pd, m)
            row[code + "A"] = odds(pa, m - j)
        # Soft book VC over-prices the home side -> our value opportunity.
        row["VCH"] = round(1.0 / (ph * (1 - edge)), 2)
        row["VCD"] = odds(pd, 0.05)
        row["VCA"] = odds(pa, 0.05)
        # Closing (Pinnacle) line at fair, for honest CLV.
        row["PSCH"] = odds(ph, 0.02); row["PSCD"] = odds(pd, 0.02)
        row["PSCA"] = odds(pa, 0.02)
        r = rng.random()
        row["FTR"] = "H" if r < ph else ("D" if r < ph + pd else "A")
        rows.append(row)
    return rows
