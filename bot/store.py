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
    fair_price REAL,
    edge REAL,
    eff_price REAL,
    settlement TEXT DEFAULT 'PENDING',
    profit REAL,
    settled_at TEXT,
    closing_fair_price REAL,
    clv REAL
);
CREATE INDEX IF NOT EXISTS idx_placements_ref ON placements(external_ref);
CREATE INDEX IF NOT EXISTS idx_placements_key ON placements(bet_key);
"""

# Columns added after the first release; ensured on every open for old DBs.
_MIGRATIONS = {
    "placements": ["fair_price", "edge", "eff_price", "closing_fair_price", "clv"],
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
            for col in columns:
                if col not in existing:
                    self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} REAL")

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
        fair_price = bet.fair_price if bet else None
        edge = bet.edge if bet else None
        eff_price = bet.eff_price if bet else None
        cur = self._conn.execute(
            """INSERT INTO placements
               (bet_key, placed_at, executor, status, requested_price,
                requested_stake, matched_price, matched_stake, external_ref,
                message, fair_price, edge, eff_price)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (result.bet_key, result.placed_at, result.executor, result.status,
             result.requested_price, result.requested_stake, result.matched_price,
             result.matched_stake, result.external_ref, result.message,
             fair_price, edge, eff_price),
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

    def record_closing(self, external_ref: str, closing_fair_price: float
                       ) -> Optional[float]:
        """Record the closing fair price (e.g. Pinnacle de-vigged price at
        kickoff) and compute Closing Line Value: clv = taken_price /
        closing_fair_price - 1. Positive CLV is the strongest predictor of a
        genuine long-term edge. Returns the CLV, or None if not found."""
        row = self._conn.execute(
            "SELECT matched_price, requested_price FROM placements "
            "WHERE external_ref = ?", (external_ref,),
        ).fetchone()
        if row is None or not closing_fair_price:
            return None
        taken = row["matched_price"] or row["requested_price"]
        clv = taken / closing_fair_price - 1.0
        self._conn.execute(
            "UPDATE placements SET closing_fair_price=?, clv=? WHERE external_ref=?",
            (closing_fair_price, clv, external_ref),
        )
        self._conn.commit()
        return clv

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
                 AVG(clv) AS avg_clv,
                 COALESCE(SUM(CASE WHEN clv > 0 THEN 1 ELSE 0 END),0) AS clv_beat,
                 COALESCE(SUM(CASE WHEN clv IS NOT NULL THEN 1 ELSE 0 END),0) AS clv_n
               FROM placements WHERE status IN ('PLACED','MATCHED','DRY_RUN')"""
        ).fetchone()
        d = dict(row)
        d["roi"] = (d["profit"] / d["settled_stake"]) if d["settled_stake"] else 0.0
        d["clv_beat_rate"] = (d["clv_beat"] / d["clv_n"]) if d["clv_n"] else 0.0
        return d

    def close(self) -> None:
        self._conn.close()
