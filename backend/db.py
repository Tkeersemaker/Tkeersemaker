"""
SQLite database for storing availability snapshots and alert subscriptions.
Uses plain sqlite3 — no ORM needed for this scale.
"""

import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime, UTC, timedelta

DB_PATH = Path(__file__).parent / "padel.db"
logger = logging.getLogger(__name__)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _now() -> str:
    return datetime.now(UTC).isoformat()


def init_db() -> None:
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS availability_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                venue_id    TEXT NOT NULL,
                venue_name  TEXT NOT NULL,
                date        TEXT NOT NULL,
                slots_json  TEXT NOT NULL,
                fetched_at  TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_venue_date
                ON availability_snapshots(venue_id, date);

            CREATE TABLE IF NOT EXISTS alert_subscriptions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                contact      TEXT NOT NULL,
                channel      TEXT NOT NULL DEFAULT 'telegram',
                venue_id     TEXT NOT NULL,
                venue_name   TEXT NOT NULL,
                date         TEXT NOT NULL,
                time_from    TEXT NOT NULL,
                time_to      TEXT NOT NULL,
                triggered    INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT NOT NULL
            );
        """)


def save_snapshot(venue_id: str, venue_name: str, date: str, slots: list) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO availability_snapshots (venue_id, venue_name, date, slots_json, fetched_at) VALUES (?, ?, ?, ?, ?)",
            (venue_id, venue_name, date, json.dumps(slots), _now()),
        )


def get_latest_snapshot(venue_id: str, date: str) -> list | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT slots_json FROM availability_snapshots WHERE venue_id = ? AND date = ? ORDER BY fetched_at DESC LIMIT 1",
            (venue_id, date),
        ).fetchone()
    return json.loads(row["slots_json"]) if row else None


def get_previous_snapshot(venue_id: str, date: str) -> list | None:
    """Return the second-most-recent snapshot (used to diff for alerts)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT slots_json FROM availability_snapshots WHERE venue_id = ? AND date = ? ORDER BY fetched_at DESC LIMIT 1 OFFSET 1",
            (venue_id, date),
        ).fetchone()
    return json.loads(row["slots_json"]) if row else None


def add_alert(contact: str, channel: str, venue_id: str, venue_name: str, date: str, time_from: str, time_to: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO alert_subscriptions (contact, channel, venue_id, venue_name, date, time_from, time_to, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (contact, channel, venue_id, venue_name, date, time_from, time_to, _now()),
        )
        return cur.lastrowid


def get_pending_alerts() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM alert_subscriptions WHERE triggered = 0"
        ).fetchall()
    return [dict(r) for r in rows]


def mark_alert_triggered(alert_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE alert_subscriptions SET triggered = 1 WHERE id = ?", (alert_id,))


def cleanup_old_snapshots(hours_back: int = 24) -> None:
    """Delete snapshots older than hours_back hours to prevent unbounded DB growth."""
    cutoff = (datetime.now(UTC) - timedelta(hours=hours_back)).isoformat()
    with get_conn() as conn:
        deleted = conn.execute(
            "DELETE FROM availability_snapshots WHERE fetched_at < ?",
            (cutoff,),
        ).rowcount
    if deleted:
        logger.info("Cleaned up %d old snapshots (older than %dh)", deleted, hours_back)
