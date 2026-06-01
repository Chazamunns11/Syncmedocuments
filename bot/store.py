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
    settlement TEXT DEFAULT 'PENDING',
    profit REAL,
    settled_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_placements_ref ON placements(external_ref);
CREATE INDEX IF NOT EXISTS idx_placements_key ON placements(bet_key);
"""


class BetStore:
    def __init__(self, db_path: str = "bets.db", csv_path: Optional[str] = "bets.csv"):
        self.db_path = db_path
        self.csv_path = csv_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

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

    def log_placement(self, result: PlacementResult) -> int:
        cur = self._conn.execute(
            """INSERT INTO placements
               (bet_key, placed_at, executor, status, requested_price,
                requested_stake, matched_price, matched_stake, external_ref,
                message)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (result.bet_key, result.placed_at, result.executor, result.status,
             result.requested_price, result.requested_stake, result.matched_price,
             result.matched_stake, result.external_ref, result.message),
        )
        self._conn.commit()
        if self.csv_path:
            self._append_csv(result)
        return cur.lastrowid

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
                 SUM(CASE WHEN settlement='WON' THEN 1 ELSE 0 END) AS won,
                 SUM(CASE WHEN settlement='LOST' THEN 1 ELSE 0 END) AS lost,
                 SUM(CASE WHEN settlement='PENDING' THEN 1 ELSE 0 END) AS pending
               FROM placements WHERE status IN ('PLACED','MATCHED','DRY_RUN')"""
        ).fetchone()
        d = dict(row)
        d["roi"] = (d["profit"] / d["settled_stake"]) if d["settled_stake"] else 0.0
        return d

    def close(self) -> None:
        self._conn.close()
