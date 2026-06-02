"""Persistence: log identified and placed bets to SQLite (+ optional CSV).

Two tables:
  * ``value_bets``   — every opportunity the detector identified.
  * ``placements``   — every placement attempt and its result, plus settlement.

Settlement (``settle``) lets you mark a placed bet WON/LOST/VOID later and
records the realised profit, so the report can show actual ROI.
"""
from __future__ import annotations

import csv
import os
import sqlite3
from typing import List, Optional

from .models import PlacementResult, ValueBet, utcnow_iso

_SCHEMA = """
CREATE TABLE IF NOT EXISTS value_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bet_key TEXT,
    identified_at TEXT,
    event_id TEXT,
    sport_key TEXT,
    commence_time TEXT,
    matchup TEXT,
    market TEXT,
    selection TEXT,
    bookmaker TEXT,
    price REAL,
    fair_prob REAL,
    fair_price REAL,
    edge REAL,
    ev REAL,
    kelly_fraction REAL,
    stake REAL
);
CREATE TABLE IF NOT EXISTS placements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bet_key TEXT,
    placed_at TEXT,
    executor TEXT,
    status TEXT,
    requested_price REAL,
    requested_stake REAL,
    matched_price REAL,
    matched_stake REAL,
    external_ref TEXT,
    message TEXT,
    event_id TEXT,
    fair_price REAL,
    edge REAL,
    eff_price REAL,
    exp_clv REAL,
    settlement TEXT DEFAULT 'PENDING',
    profit REAL,
    settled_at TEXT,
    closing_fair_price REAL,
    clv REAL
);
CREATE INDEX IF NOT EXISTS idx_placements_ref ON placements(external_ref);
CREATE INDEX IF NOT EXISTS idx_placements_key ON placements(bet_key);
CREATE INDEX IF NOT EXISTS idx_placements_event ON placements(event_id);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value REAL
);
"""

# Columns added after the first release; ensured on every open for old DBs.
# (column_name, sql_type)
_MIGRATIONS = {
    "placements": [
        ("fair_price", "REAL"), ("edge", "REAL"), ("eff_price", "REAL"),
        ("exp_clv", "REAL"), ("closing_fair_price", "REAL"), ("clv", "REAL"),
        ("event_id", "TEXT"),
        # True closing line value: against the venue's OWN closing price
        # (Betfair near-off back price), the gold-standard CLV for an exchange
        # bettor, alongside the model-based closing fair price.
        ("closing_market_price", "REAL"), ("clv_market", "REAL"),
        ("commission", "REAL"),
    ],
}


class BetStore:
    def __init__(self, db_path: str = "bets.db", csv_path: Optional[str] = "bets.csv"):
        self.db_path = db_path
        self.csv_path = csv_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        for table, columns in _MIGRATIONS.items():
            existing = {r["name"] for r in
                        self._conn.execute(f"PRAGMA table_info({table})")}
            for col, sqltype in columns:
                if col not in existing:
                    self._conn.execute(
                        f"ALTER TABLE {table} ADD COLUMN {col} {sqltype}")

    # -- writes ------------------------------------------------------------
    def log_value_bet(self, bet: ValueBet) -> None:
        self._conn.execute(
            """INSERT INTO value_bets
               (bet_key, identified_at, event_id, sport_key, commence_time,
                matchup, market, selection, bookmaker, price, fair_prob,
                fair_price, edge, ev, kelly_fraction, stake)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (bet.key, bet.identified_at, bet.event_id, bet.sport_key,
             bet.commence_time, bet.matchup, bet.market, bet.selection,
             bet.bookmaker, bet.price, bet.fair_prob, bet.fair_price,
             bet.edge, bet.ev, bet.kelly_fraction, bet.stake),
        )
        self._conn.commit()

    def log_placement(self, result: PlacementResult,
                      bet: Optional[ValueBet] = None) -> int:
        event_id = bet.event_id if bet else None
        fair_price = bet.fair_price if bet else None
        edge = bet.edge if bet else None
        eff_price = bet.eff_price if bet else None
        exp_clv = bet.exp_clv if bet else None
        cur = self._conn.execute(
            """INSERT INTO placements
               (bet_key, placed_at, executor, status, requested_price,
                requested_stake, matched_price, matched_stake, external_ref,
                message, event_id, fair_price, edge, eff_price, exp_clv)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (result.bet_key, result.placed_at, result.executor, result.status,
             result.requested_price, result.requested_stake, result.matched_price,
             result.matched_stake, result.external_ref, result.message,
             event_id, fair_price, edge, eff_price, exp_clv),
        )
        self._conn.commit()
        if self.csv_path:
            self._append_csv(result)
        return cur.lastrowid

    def already_placed(self, bet_key: str) -> bool:
        """True if this opportunity already has a non-failed placement, so the
        continuous loop won't bet the same selection twice."""
        row = self._conn.execute(
            "SELECT 1 FROM placements WHERE bet_key = ? "
            "AND status IN ('PLACED','MATCHED','DRY_RUN') LIMIT 1",
            (bet_key,),
        ).fetchone()
        return row is not None

    def already_placed_event(self, event_id: str) -> bool:
        """True if this EVENT already has a non-failed placement — enforces the
        one-bet-per-event rule across runs."""
        if not event_id:
            return False
        row = self._conn.execute(
            "SELECT 1 FROM placements WHERE event_id = ? "
            "AND status IN ('PLACED','MATCHED','DRY_RUN') LIMIT 1",
            (event_id,),
        ).fetchone()
        return row is not None

    def unrecorded_closing(self):
        """Placed bets that don't yet have a closing line recorded (for CLV)."""
        return self._conn.execute(
            "SELECT external_ref, event_id, bet_key FROM placements "
            "WHERE status IN ('PLACED','MATCHED','DRY_RUN') "
            "AND closing_fair_price IS NULL AND external_ref IS NOT NULL"
        ).fetchall()

    def record_closing(self, external_ref: str, closing_fair_price: float,
                       closing_market_price: Optional[float] = None
                       ) -> Optional[float]:
        """Record the closing line and compute Closing Line Value.

        * ``clv`` = taken_price / closing_fair_price - 1  (vs our model's fair
          price at kickoff).
        * ``clv_market`` = taken_price / closing_market_price - 1  (vs the venue's
          OWN closing back price — the gold standard for an exchange bettor).

        Positive CLV is the strongest predictor of a genuine long-term edge.
        Returns the model CLV, or None if not found."""
        row = self._conn.execute(
            "SELECT matched_price, requested_price FROM placements "
            "WHERE external_ref = ?", (external_ref,),
        ).fetchone()
        if row is None or not closing_fair_price:
            return None
        taken = row["matched_price"] or row["requested_price"]
        clv = taken / closing_fair_price - 1.0
        clv_market = (taken / closing_market_price - 1.0
                      if closing_market_price else None)
        self._conn.execute(
            "UPDATE placements SET closing_fair_price=?, clv=?, "
            "closing_market_price=?, clv_market=? WHERE external_ref=?",
            (closing_fair_price, clv, closing_market_price, clv_market, external_ref),
        )
        self._conn.commit()
        return clv

    def settle_from_betfair(self, cleared) -> int:
        """Settle placements from Betfair cleared-order reports (hands-off).
        Each item must expose bet_id and profit. Matches on external_ref =
        bet_id. Returns the number settled."""
        n = 0
        for o in cleared:
            bet_id = getattr(o, "bet_id", None) or (
                o.get("betId") if isinstance(o, dict) else None)
            profit = getattr(o, "profit", None)
            if profit is None and isinstance(o, dict):
                profit = o.get("profit")
            if bet_id is None or profit is None:
                continue
            outcome = "WON" if profit > 0 else ("LOST" if profit < 0 else "VOID")
            cur = self._conn.execute(
                "UPDATE placements SET settlement=?, profit=?, settled_at=? "
                "WHERE external_ref=? AND settlement='PENDING'",
                (outcome, float(profit), utcnow_iso(), str(bet_id)),
            )
            n += cur.rowcount
        self._conn.commit()
        return n

    def _append_csv(self, result: PlacementResult) -> None:
        new = not os.path.exists(self.csv_path)
        with open(self.csv_path, "a", newline="") as fh:
            writer = csv.writer(fh)
            if new:
                writer.writerow([
                    "placed_at", "bet_key", "executor", "status",
                    "requested_price", "requested_stake", "matched_price",
                    "matched_stake", "external_ref", "message",
                ])
            writer.writerow([
                result.placed_at, result.bet_key, result.executor, result.status,
                result.requested_price, result.requested_stake,
                result.matched_price, result.matched_stake,
                result.external_ref, result.message,
            ])

    def settle(self, external_ref: str, outcome: str) -> Optional[float]:
        """Mark a placement WON/LOST/VOID and record realised profit.

        profit = stake*(price-1) on a win, -stake on a loss, 0 on a void.
        Returns the profit, or None if the placement wasn't found.
        """
        outcome = outcome.upper()
        row = self._conn.execute(
            "SELECT matched_price, requested_price, matched_stake, requested_stake "
            "FROM placements WHERE external_ref = ?",
            (external_ref,),
        ).fetchone()
        if row is None:
            return None
        price = row["matched_price"] or row["requested_price"]
        stake = row["matched_stake"] or row["requested_stake"]
        if outcome == "WON":
            profit = stake * (price - 1.0)
        elif outcome == "LOST":
            profit = -stake
        elif outcome == "VOID":
            profit = 0.0
        else:
            raise ValueError("outcome must be WON, LOST or VOID")
        self._conn.execute(
            "UPDATE placements SET settlement=?, profit=?, settled_at=? "
            "WHERE external_ref=?",
            (outcome, profit, utcnow_iso(), external_ref),
        )
        self._conn.commit()
        return profit

    # -- reads -------------------------------------------------------------
    def recent_placements(self, limit: int = 50) -> List[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM placements ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()

    def clv_samples(self, market: bool = True) -> List[float]:
        """Per-bet CLV values for statistical validation. ``market`` selects CLV
        vs the venue's own close (the real scoreboard); otherwise vs our model."""
        col = "clv_market" if market else "clv"
        rows = self._conn.execute(
            f"SELECT {col} AS c FROM placements WHERE {col} IS NOT NULL "
            "AND status IN ('PLACED','MATCHED','DRY_RUN')"
        ).fetchall()
        return [float(r["c"]) for r in rows]

    def summary(self) -> dict:
        row = self._conn.execute(
            """SELECT
                 COUNT(*) AS n,
                 COALESCE(SUM(requested_stake),0) AS staked,
                 COALESCE(SUM(CASE WHEN settlement!='PENDING' THEN profit END),0) AS profit,
                 COALESCE(SUM(CASE WHEN settlement!='PENDING' THEN requested_stake END),0) AS settled_stake,
                 COALESCE(SUM(CASE WHEN settlement='WON' THEN 1 ELSE 0 END),0) AS won,
                 COALESCE(SUM(CASE WHEN settlement='LOST' THEN 1 ELSE 0 END),0) AS lost,
                 COALESCE(SUM(CASE WHEN settlement='PENDING' THEN 1 ELSE 0 END),0) AS pending,
                 AVG(edge) AS avg_edge,
                 AVG(exp_clv) AS avg_exp_clv,
                 AVG(clv) AS avg_clv,
                 AVG(clv_market) AS avg_clv_market,
                 COALESCE(SUM(CASE WHEN clv > 0 THEN 1 ELSE 0 END),0) AS clv_beat,
                 COALESCE(SUM(CASE WHEN clv IS NOT NULL THEN 1 ELSE 0 END),0) AS clv_n,
                 COALESCE(SUM(CASE WHEN clv_market > 0 THEN 1 ELSE 0 END),0) AS clv_mkt_beat,
                 COALESCE(SUM(CASE WHEN clv_market IS NOT NULL THEN 1 ELSE 0 END),0) AS clv_mkt_n
               FROM placements WHERE status IN ('PLACED','MATCHED','DRY_RUN')"""
        ).fetchone()
        d = dict(row)
        d["roi"] = (d["profit"] / d["settled_stake"]) if d["settled_stake"] else 0.0
        d["clv_beat_rate"] = (d["clv_beat"] / d["clv_n"]) if d["clv_n"] else 0.0
        d["clv_mkt_beat_rate"] = (d["clv_mkt_beat"] / d["clv_mkt_n"]) if d["clv_mkt_n"] else 0.0
        return d

    def realised_profit(self) -> float:
        """Total settled profit across all placements (for live bankroll)."""
        row = self._conn.execute(
            "SELECT COALESCE(SUM(profit),0) AS p FROM placements "
            "WHERE settlement != 'PENDING'").fetchone()
        return float(row["p"] or 0.0)

    def staked_since(self, iso_time: str) -> float:
        """Total stake placed since an ISO timestamp (for daily caps)."""
        row = self._conn.execute(
            "SELECT COALESCE(SUM(requested_stake),0) AS s FROM placements "
            "WHERE placed_at >= ? AND status IN ('PLACED','MATCHED','DRY_RUN')",
            (iso_time,)).fetchone()
        return float(row["s"] or 0.0)

    def count_since(self, iso_time: str) -> int:
        """Number of placements since an ISO timestamp (for daily count caps)."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM placements WHERE placed_at >= ? "
            "AND status IN ('PLACED','MATCHED','DRY_RUN')", (iso_time,)).fetchone()
        return int(row["n"] or 0)

    # -- small key/value state (peak bankroll, etc.) ----------------------
    def get_meta(self, key: str, default: float = 0.0) -> float:
        row = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return float(row["value"]) if row else default

    def set_meta(self, key: str, value: float) -> None:
        self._conn.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        self._conn.commit()

    def count_open(self) -> int:
        """Placements not yet settled (open exposure positions)."""
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM placements "
            "WHERE settlement='PENDING' AND status IN ('PLACED','MATCHED')"
        ).fetchone()
        return int(row["n"] or 0)

    def open_exposure(self) -> float:
        """Total staked on placements not yet settled (money at risk)."""
        row = self._conn.execute(
            "SELECT COALESCE(SUM(requested_stake),0) AS s FROM placements "
            "WHERE settlement='PENDING' AND status IN ('PLACED','MATCHED')"
        ).fetchone()
        return float(row["s"] or 0.0)

    def close(self) -> None:
        self._conn.close()
