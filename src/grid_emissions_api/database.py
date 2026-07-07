"""SQLite storage layer for emissions intensity data."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import settings
from .models import IntensityDataPoint


def _utc_iso(dt: datetime) -> str:
    """Return a canonical UTC ISO-8601 string for `dt`.

    Timestamps are compared as text (lexicographically) by SQLite, so every
    value we store or query with must share one canonical representation for
    text order to equal chronological order. Tz-aware datetimes are converted
    to UTC; naive datetimes are assumed to already be UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _db_path() -> Path:
    return Path(settings.database_path)


def get_connection() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create the schema if it doesn't exist."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS intensity (
                country      TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                intensity    REAL NOT NULL,
                generation_mix TEXT NOT NULL,
                is_estimated INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (country, timestamp_utc)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_intensity_country_ts
            ON intensity (country, timestamp_utc)
        """)


def upsert_intensity(
    country: str,
    data_points: list[IntensityDataPoint],
) -> int:
    """Insert or replace intensity data points. Returns count of rows written."""
    if not data_points:
        return 0
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO intensity
                (country, timestamp_utc, intensity, generation_mix, is_estimated)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    country,
                    _utc_iso(dp.timestamp),
                    dp.intensity,
                    json.dumps(dp.generation_mix),
                    int(dp.is_estimated),
                )
                for dp in data_points
            ],
        )
    return len(data_points)


def query_intensity(
    country: str,
    start: datetime,
    end: datetime,
) -> list[IntensityDataPoint]:
    """Query intensity data for a country and time range."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT timestamp_utc, intensity, generation_mix, is_estimated
            FROM intensity
            WHERE country = ? AND timestamp_utc >= ? AND timestamp_utc < ?
            ORDER BY timestamp_utc
            """,
            (country, _utc_iso(start), _utc_iso(end)),
        ).fetchall()

    return [
        IntensityDataPoint(
            timestamp=datetime.fromisoformat(row[0]),
            intensity=row[1],
            generation_mix=json.loads(row[2]),
            is_estimated=bool(row[3]),
        )
        for row in rows
    ]


def query_latest(country: str) -> list[IntensityDataPoint]:
    """Get the most recent data point for a country."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT timestamp_utc, intensity, generation_mix, is_estimated
            FROM intensity
            WHERE country = ?
            ORDER BY timestamp_utc DESC
            LIMIT 1
            """,
            (country,),
        ).fetchone()

    if row is None:
        return []

    return [
        IntensityDataPoint(
            timestamp=datetime.fromisoformat(row[0]),
            intensity=row[1],
            generation_mix=json.loads(row[2]),
            is_estimated=bool(row[3]),
        )
    ]


def row_count(country: str | None = None) -> int:
    """Count rows, optionally filtered by country."""
    with get_connection() as conn:
        if country:
            return conn.execute(
                "SELECT COUNT(*) FROM intensity WHERE country = ?", (country,)
            ).fetchone()[0]
        return conn.execute("SELECT COUNT(*) FROM intensity").fetchone()[0]
