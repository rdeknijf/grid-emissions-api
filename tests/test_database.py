"""Tests for SQLite storage layer."""

import os
import tempfile
from datetime import datetime, timezone

import pytest

from grid_emissions_api.database import (
    init_db,
    query_intensity,
    query_latest,
    row_count,
    upsert_intensity,
)
from grid_emissions_api.models import IntensityDataPoint


@pytest.fixture(autouse=True)
def _tmp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        monkeypatch.setenv("DATABASE_PATH", db_path)
        from grid_emissions_api.config import Settings

        monkeypatch.setattr("grid_emissions_api.database.settings", Settings())
        init_db()
        yield


def _make_point(hour: int, intensity: float = 300.0) -> IntensityDataPoint:
    return IntensityDataPoint(
        timestamp=datetime(2026, 3, 19, hour, 0, tzinfo=timezone.utc),
        intensity=intensity,
        generation_mix={"gas_ccgt": 0.6, "wind_onshore": 0.4},
    )


def test_upsert_and_query():
    points = [_make_point(0), _make_point(1), _make_point(2)]
    upsert_intensity("NL", points)

    result = query_intensity(
        "NL",
        datetime(2026, 3, 19, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 19, 3, tzinfo=timezone.utc),
    )
    assert len(result) == 3
    assert result[0].intensity == 300.0


def test_upsert_replaces_existing():
    upsert_intensity("NL", [_make_point(0, intensity=300.0)])
    upsert_intensity("NL", [_make_point(0, intensity=400.0)])

    result = query_intensity(
        "NL",
        datetime(2026, 3, 19, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 19, 1, tzinfo=timezone.utc),
    )
    assert len(result) == 1
    assert result[0].intensity == 400.0


def test_query_filters_by_country():
    upsert_intensity("NL", [_make_point(0)])
    upsert_intensity("DE", [_make_point(0, intensity=500.0)])

    result = query_intensity(
        "NL",
        datetime(2026, 3, 19, 0, tzinfo=timezone.utc),
        datetime(2026, 3, 19, 1, tzinfo=timezone.utc),
    )
    assert len(result) == 1
    assert result[0].intensity == 300.0


def test_query_filters_by_time_range():
    points = [_make_point(h) for h in range(5)]
    upsert_intensity("NL", points)

    result = query_intensity(
        "NL",
        datetime(2026, 3, 19, 1, tzinfo=timezone.utc),
        datetime(2026, 3, 19, 3, tzinfo=timezone.utc),
    )
    assert len(result) == 2


def test_query_latest():
    points = [_make_point(0, 300.0), _make_point(1, 350.0), _make_point(2, 400.0)]
    upsert_intensity("NL", points)

    result = query_latest("NL")
    assert len(result) == 1
    assert result[0].intensity == 400.0
    assert result[0].timestamp.hour == 2


def test_query_latest_empty():
    result = query_latest("NL")
    assert result == []


def test_row_count():
    upsert_intensity("NL", [_make_point(0), _make_point(1)])
    upsert_intensity("DE", [_make_point(0)])

    assert row_count() == 3
    assert row_count("NL") == 2
    assert row_count("DE") == 1


def test_generation_mix_roundtrips():
    mix = {"gas_ccgt": 0.6, "wind_onshore": 0.35, "solar": 0.05}
    point = IntensityDataPoint(
        timestamp=datetime(2026, 3, 19, 0, tzinfo=timezone.utc),
        intensity=300.0,
        generation_mix=mix,
    )
    upsert_intensity("NL", [point])

    result = query_latest("NL")
    assert result[0].generation_mix == mix
