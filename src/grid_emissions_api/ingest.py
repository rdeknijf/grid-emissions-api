"""Ingestion: fetch ENTSO-E data and store in SQLite.

Usage:
    # Fetch last 24 hours for all countries:
    uv run python -m grid_emissions_api.ingest

    # Backfill from a start date:
    uv run python -m grid_emissions_api.ingest --backfill --start 2024-01-01
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

from .database import init_db, row_count, upsert_intensity
from .emissions import calculate_intensity
from .entsoe_client import fetch_generation
from .models import BIDDING_ZONES

COUNTRIES = list(BIDDING_ZONES.keys())


async def ingest_range(country: str, start: datetime, end: datetime) -> int:
    """Fetch and store intensity data for a country and time range."""
    generation = await fetch_generation(country, start, end)
    data = calculate_intensity(generation)
    return upsert_intensity(country, data)


async def ingest_recent(hours: int = 48) -> None:
    """Fetch recent data for all countries."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(hours=hours)
    end = now

    for country in COUNTRIES:
        try:
            n = await ingest_range(country, start, end)
            print(f"  {country}: {n} data points")
        except Exception as e:
            print(f"  {country}: ERROR {e}", file=sys.stderr)


async def backfill(start_date: datetime, end_date: datetime | None = None) -> None:
    """Backfill historical data in 30-day chunks.

    ENTSO-E allows max ~1 year per request but returns faster with smaller ranges.
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

    for country in COUNTRIES:
        print(f"\n{country}:")
        chunk_start = start_date
        total = 0
        while chunk_start < end_date:
            chunk_end = min(chunk_start + timedelta(days=30), end_date)
            try:
                n = await ingest_range(country, chunk_start, chunk_end)
                total += n
                print(f"  {chunk_start.date()} → {chunk_end.date()}: {n} points")
            except Exception as e:
                print(
                    f"  {chunk_start.date()} → {chunk_end.date()}: ERROR {e}",
                    file=sys.stderr,
                )
            chunk_start = chunk_end
            await asyncio.sleep(0.5)  # be kind to ENTSO-E rate limits
        print(f"  Total: {total} points")

    print(f"\nDatabase: {row_count()} total rows")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest ENTSO-E data")
    parser.add_argument(
        "--backfill", action="store_true", help="Backfill historical data"
    )
    parser.add_argument(
        "--start",
        type=str,
        default="2024-01-01",
        help="Backfill start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="Backfill end date (YYYY-MM-DD), defaults to now",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=48,
        help="Hours to fetch for recent ingestion (default: 48)",
    )
    args = parser.parse_args()

    init_db()

    if args.backfill:
        start = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = None
        if args.end:
            end = datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        print(f"Backfilling from {args.start}...")
        asyncio.run(backfill(start, end))
    else:
        print(f"Ingesting last {args.hours} hours...")
        asyncio.run(ingest_recent(args.hours))
        print(f"Database: {row_count()} total rows")


if __name__ == "__main__":
    main()
