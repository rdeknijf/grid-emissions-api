"""Tests for ingest error logging and backfill chunking."""

import itertools
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from grid_emissions_api import ingest
from grid_emissions_api.entsoe_client import _MAX_SERIES_LAG
from grid_emissions_api.ingest import _describe_error


def test_http_error_log_omits_the_token():
    url = "https://web-api.tp.entsoe.eu/api?securityToken=secret-token&in_Domain=X"
    request = httpx.Request("GET", url)
    response = httpx.Response(599, request=request)
    error = httpx.HTTPStatusError(
        "Server error for url " + url, request=request, response=response
    )
    message = _describe_error(error)
    assert "secret-token" not in message
    assert message == "HTTPStatusError: HTTP 599"


def test_empty_error_message_still_names_the_error():
    assert _describe_error(httpx.ReadTimeout("")) == "ReadTimeout"


@pytest.mark.asyncio
async def test_backfill_chunks_overlap_by_the_series_lag(monkeypatch):
    calls: list[tuple[str, datetime, datetime]] = []

    async def fake_ingest_range(country, start, end):
        calls.append((country, start, end))
        return 0

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(ingest, "COUNTRIES", ["NL"])
    monkeypatch.setattr(ingest, "ingest_range", fake_ingest_range)
    monkeypatch.setattr(ingest.asyncio, "sleep", no_sleep)
    monkeypatch.setattr(ingest, "row_count", lambda: 0)

    start = datetime(2026, 10, 1, tzinfo=UTC)
    end = datetime(2026, 12, 15, tzinfo=UTC)
    await ingest.backfill(start, end)

    spans = [(s, e) for _, s, e in calls]
    assert spans[0][0] == start
    assert spans[-1][1] == end
    for (_, prev_end), (next_start, _) in itertools.pairwise(spans):
        assert next_start == prev_end - _MAX_SERIES_LAG
    assert all(e - s <= timedelta(days=30) for s, e in spans)
    assert len(spans) == 3
